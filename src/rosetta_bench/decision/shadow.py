"""Shadow-mode intake decisions over a labelled routing corpus.

For each case: deterministic gates -> masked, fail-closed state -> one batched
question call -> pure policy reduction -> receipt. Shadow mode records the proposed
route while the executed route stays the case's baseline route. Replay re-runs the
same pipeline against the recorded exchanges and must reproduce every decision.
"""
from __future__ import annotations

import hashlib
import json
import platform
import random
import re
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import rosetta_core
from rosetta_core.decision import (
    CONTRACT_VERSION,
    RECEIPT_VERSION,
    STATE_SCHEMA_VERSION,
    AnswerBatch,
    Evidence,
    GateResult,
    IntakeQuestions,
    IntakeThresholds,
    Outcome,
    Policy,
    ProviderError,
    RouteRef,
    StateRejected,
    assert_no_secrets,
    build_state,
    new_receipt_id,
    reduce,
    state_digest,
    validate_batch,
    validate_receipt,
    wire_state,
)
from rosetta_core.decision.contracts import canonical_json

import rosetta_bench
from rosetta_bench.pricing import estimate_cost_v2
from rosetta_bench.provenance import git_state

from .battery import intake_battery
from .masking import Masker
from .profiles import ProviderProfile
from .systemone import SystemOneAdapter
from .transport import BudgetExceeded, ReplayTransport, Transport

APPROVED_DATA_CLASSES = ("synthetic",)
_VERSIONED = re.compile(r"\d+\.\d+\.\d+")
EVIDENCE_MAX_AGE = timedelta(days=1)
PLACEHOLDER_THRESHOLDS = {"fit_yes": 0.7, "fit_no": 0.3, "route_default": 0.6}


@dataclass(frozen=True)
class RoutingCase:
    case_id: str
    category: str
    language: str
    data_class: str
    request_text: str
    eligible_routes: tuple[str, ...]
    baseline_route: str
    label_fits: bool
    label_route: str | None
    label_source: str


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_routing_corpus(corpus_dir: Path) -> tuple[list[dict], list[RoutingCase], str]:
    corpus_dir = Path(corpus_dir)
    routes_text = (corpus_dir / "routes.json").read_text(encoding="utf-8")
    cases_text = (corpus_dir / "cases.jsonl").read_text(encoding="utf-8")
    routes = json.loads(routes_text)["routes"]
    cases = []
    for line in cases_text.splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        cases.append(RoutingCase(
            case_id=raw["case_id"], category=raw["category"], language=raw["language"],
            data_class=raw["data_class"], request_text=raw["request_text"],
            eligible_routes=tuple(raw["eligible_routes"]), baseline_route=raw["baseline_route"],
            label_fits=raw["label_fits"], label_route=raw["label_route"], label_source=raw["label_source"],
        ))
    digest = _sha(canonical_json({"routes": json.loads(routes_text), "cases": [json.loads(l) for l in cases_text.splitlines() if l.strip()]}))
    return routes, cases, digest


def placeholder_policy(profile: ProviderProfile, served_model: str, qset) -> Policy:
    return Policy(
        policy_id="intake-placeholder",
        version="0.1",
        provider=profile.name,
        served_model=served_model,
        qset_id=qset.set_id,
        qset_hash=qset.content_hash(),
        thresholds=IntakeThresholds(
            fit_yes=PLACEHOLDER_THRESHOLDS["fit_yes"], fit_no=PLACEHOLDER_THRESHOLDS["fit_no"],
            requirements_yes=0.7, requirements_no=0.3,
            route_min_p={"*": PLACEHOLDER_THRESHOLDS["route_default"]},
        ),
        calibrated=False,
        frozen_at="2026-11-09T00:00:00Z",
        questions=IntakeQuestions(requirements=None),
    )


def _gates(case: RoutingCase) -> GateResult:
    deny = () if case.data_class in APPROVED_DATA_CLASSES else (f"DATA_CLASS_NOT_APPROVED:{case.data_class}",)
    return GateResult(eligible_routes=case.eligible_routes, deny_reasons=deny)


def _answers_json(result) -> dict | None:
    if isinstance(result, AnswerBatch):
        return {qid: asdict(answer) for qid, answer in result.answers.items()}
    return None


def _repo_state(module) -> dict | None:
    return git_state(Path(module.__file__).resolve().parents[2])


class _Writer:
    def __init__(self, out_dir: Path):
        self.out = Path(out_dir)
        if (self.out / "manifest.json").exists():
            raise FileExistsError(f"a run already exists in {self.out}; choose a new --out directory")
        self.out.mkdir(parents=True, exist_ok=True)

    def append(self, name: str, record: dict) -> None:
        with (self.out / name).open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, allow_nan=True) + "\n")

    def write_json(self, name: str, data: dict) -> None:
        (self.out / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def run_shadow(
    corpus_dir: Path,
    profile: ProviderProfile,
    transport: Transport,
    out_dir: Path,
    *,
    seed: int,
    api_key: str | None = None,
    live: bool = False,
    state_time: str | None = None,
    model: str | None = None,
    max_transport_retries: int = 2,
) -> Path:
    routes, cases, corpus_digest = load_routing_corpus(corpus_dir)
    model = model or profile.default_model
    expected_served = profile.expected_served_model or model
    qset = intake_battery(routes)
    policy = placeholder_policy(profile, expected_served, qset)
    route_refs = {r["id"]: RouteRef(r["id"], r["description"], _sha(canonical_json(r))) for r in routes}
    now = datetime.fromisoformat(state_time) if state_time else datetime.now(timezone.utc).replace(microsecond=0)
    order = [case.case_id for case in cases]
    random.Random(seed).shuffle(order)
    by_id = {case.case_id: case for case in cases}
    run_id = f"dec-{uuid.uuid4().hex[:12]}"
    repos = {"core": _repo_state(rosetta_core), "bench": _repo_state(rosetta_bench)}

    writer = _Writer(out_dir)
    manifest = {
        "schema": "rosetta-bench/decision-run@1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "corpus_dir": str(Path(corpus_dir).resolve()),
        "corpus_digest": corpus_digest,
        "provider": {"profile": profile.name, "endpoint": profile.endpoint, "requested_model": model,
                     "expected_served_model": expected_served, "notes": profile.notes},
        "synthetic": profile.name == "fake",
        "live": live,
        "seed": seed,
        "order": order,
        "state_time": now.isoformat(),
        "question_set": {"set_id": qset.set_id, "version": qset.version, "hash": qset.content_hash()},
        "policy": {"policy_id": policy.policy_id, "version": policy.version, "calibrated": policy.calibrated, "thresholds": PLACEHOLDER_THRESHOLDS},
        "max_transport_retries": max_transport_retries,
        "repos": repos,
        "environment": {"python": sys.version.split()[0], "platform": platform.platform()},
        "stopped_early": None,
    }
    writer.write_json("manifest.json", manifest)

    adapter = SystemOneAdapter(profile, transport, model=model, api_key=api_key, max_transport_retries=max_transport_retries)
    forbidden_extra = (api_key,) if api_key else ()
    for case_id in order:
        case = by_id[case_id]
        masker = Masker()
        gates = _gates(case)
        evidence = (Evidence("request.text", masker.mask_value(case.request_text), f"corpus:{case.case_id}", now.isoformat()),)
        state = None
        try:
            state = build_state(
                request_id=case.case_id, objective="Choose the workflow for this request from the listed routes.",
                constraints={"data_class": case.data_class}, evidence=evidence,
                eligible_routes=tuple(route_refs[r] for r in route_refs), policy_ref=f"{policy.policy_id}@{policy.version}",
                required=("request.text",), max_age={"request.text": EVIDENCE_MAX_AGE}, now=now,
            )
        except StateRejected as rejected:
            gates = GateResult(gates.eligible_routes, gates.deny_reasons, rejected.missing + rejected.stale + rejected.problems)

        ask = None
        if not gates.deny_reasons and not gates.missing_evidence and state is not None:
            try:
                ask = adapter.ask(wire_state(state), qset, context={"case_id": case.case_id})
            except BudgetExceeded as exc:
                manifest["stopped_early"] = str(exc)
                break
            for exchange in ask.exchanges:
                assert_no_secrets(exchange, forbidden=masker.originals + forbidden_extra)
                writer.append("exchanges.jsonl", exchange)
        result = ask.result if ask else None
        recommendation = reduce(gates, result, policy, qset)
        violations = [asdict(v) for v in validate_batch(result, qset)] if isinstance(result, AnswerBatch) else []
        decision = {
            "case_id": case.case_id, "category": case.category, "language": case.language,
            "label_fits": case.label_fits, "label_route": case.label_route, "eligible_routes": list(case.eligible_routes),
            "outcome": recommendation.outcome.value, "route": recommendation.route,
            "reason_codes": list(recommendation.reason_codes), "signals": dict(recommendation.signals),
            "answers": _answers_json(result), "violations": violations,
            "provider_error": {"kind": result.kind.value, "detail": result.detail} if isinstance(result, ProviderError) else None,
            "served_model": result.served_model if isinstance(result, AnswerBatch) else None,
            "input_tokens": ask.input_tokens if ask else None, "calls": ask.calls if ask else 0,
            "transport_retries": ask.transport_retries if ask else 0, "decision_ms": ask.elapsed_ms if ask else 0.0,
            "tokens_remaining": ask.tokens_remaining if ask else None,
        }
        served = result.served_model if isinstance(result, AnswerBatch) else None
        receipt = {
            "receipt_version": RECEIPT_VERSION, "receipt_id": new_receipt_id(), "run_id": run_id,
            "trial_id": f"{run_id}:{case.case_id}", "case_id": case.case_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "repos": {name: (state_ or {}).get("sha") for name, state_ in repos.items()},
            "contract_version": CONTRACT_VERSION,
            "state": {
                "schema_version": STATE_SCHEMA_VERSION,
                "digest": state_digest(state) if state else _sha(case.case_id),
                "snapshot_ref": f"exchanges.jsonl#{case.case_id}" if ask and ask.exchanges else None,
            },
            "replay": "available" if ask and ask.exchanges else "unavailable",
            "question_set": {"set_id": qset.set_id, "version": qset.version, "hash": qset.content_hash()},
            "policy": {"policy_id": policy.policy_id, "version": policy.version, "calibrated": policy.calibrated},
            "provider": {"name": profile.name, "requested_model": model, "served_model": served,
                         "revision_known": bool(served and served == expected_served
                                                and (profile.pins_versions or _VERSIONED.search(served)))},
            "answers_ref": f"decisions.jsonl#{case.case_id}",
            "recommendation": {"outcome": recommendation.outcome.value, "route": recommendation.route,
                               "reason_codes": list(recommendation.reason_codes)},
            "executed_route": case.baseline_route,
            "mode": "shadow",
            "generator": None,
            "usage": {"decision_input_tokens": ask.input_tokens if ask else 0},
            "cost": estimate_cost_v2(profile.pricing_tool, model, ask.input_tokens if ask else 0, 0).to_dict(),
            "timings_ms": {"decision": ask.elapsed_ms if ask else 0.0},
            "retries": {"transport": ask.transport_retries if ask else 0, "semantic": 0},
            "output_digest": None,
            "outcome": {"verified_success": None, "checks": {
                "fit_matches_label": None if recommendation.outcome in (Outcome.DENY, Outcome.FALLBACK, Outcome.ABSTAIN, Outcome.NEED_EVIDENCE)
                else (recommendation.outcome is Outcome.ACCEPT) == case.label_fits,
                "route_matches_label": None if recommendation.route is None else recommendation.route == case.label_route,
            }},
            "override": None,
        }
        validate_receipt(receipt)
        assert_no_secrets(receipt, forbidden=masker.originals + forbidden_extra)
        assert_no_secrets(decision, forbidden=masker.originals + forbidden_extra)
        writer.append("decisions.jsonl", decision)
        writer.append("receipts.jsonl", receipt)
    writer.write_json("manifest.json", manifest)
    return writer.out


@dataclass
class ReplayReport:
    cases: int
    mismatches: list[str]


def _lines(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def replay_run(run_dir: Path, profiles: dict | None = None) -> ReplayReport:
    from .profiles import PROFILES

    run_dir = Path(run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    corpus_dir = Path(manifest["corpus_dir"])
    _, _, digest = load_routing_corpus(corpus_dir)
    if digest != manifest["corpus_digest"]:
        raise ValueError("corpus changed since the run; replay would not be like for like")
    from dataclasses import replace

    profile = (profiles or PROFILES)[manifest["provider"]["profile"]]
    profile = replace(profile, expected_served_model=manifest["provider"].get("expected_served_model"))
    original = {d["case_id"]: d for d in _lines(run_dir / "decisions.jsonl")}
    exchanges = _lines(run_dir / "exchanges.jsonl")

    import tempfile

    with tempfile.TemporaryDirectory(prefix="rosetta-replay-") as tmp:
        replayed_dir = run_shadow(
            corpus_dir, profile, ReplayTransport(exchanges), Path(tmp) / "replay",
            seed=manifest["seed"], api_key=f"no-key-{uuid.uuid4().hex}" if profile.api_key_env else None,
            state_time=manifest["state_time"], model=manifest["provider"]["requested_model"],
            max_transport_retries=manifest["max_transport_retries"],
        )
        replayed = {d["case_id"]: d for d in _lines(replayed_dir / "decisions.jsonl")}
    keys = ("outcome", "route", "reason_codes", "signals")
    mismatches = sorted(
        case_id for case_id, decision in original.items()
        if case_id not in replayed or any(decision[k] != replayed[case_id][k] for k in keys)
    )
    return ReplayReport(cases=len(original), mismatches=mismatches)
