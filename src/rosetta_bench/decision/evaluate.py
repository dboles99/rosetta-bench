"""Decision-eval harness: typed questions over corpus items with gold known by construction.

Per item: masked, fail-closed state (build_state) -> one batched call for the item's
question set -> validation -> placeholder thresholds -> verdicts scored against gold ->
receipt. No policy acts on the verdicts (mode "shadow", no executed route). Provider
failures and invalid answers become typed errors, never verdicts. Replay re-runs the
same pipeline against the recorded exchanges and must reproduce every verdict.
"""
from __future__ import annotations

import hashlib
import json
import platform
import random
import re
import sys
import tempfile
import uuid
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import rosetta_core
from rosetta_core.decision import (
    CONTRACT_VERSION,
    RECEIPT_VERSION,
    STATE_SCHEMA_VERSION,
    AnswerBatch,
    Evidence,
    NoulAnswer,
    Primitive,
    ProviderError,
    RouteRef,
    ScoreAnswer,
    StateRejected,
    assert_no_secrets,
    build_state,
    new_receipt_id,
    state_digest,
    validate_batch,
    validate_receipt,
    wire_state,
)
from rosetta_core.decision.contracts import canonical_json

import rosetta_bench
from rosetta_bench.pricing import estimate_cost_v2
from rosetta_bench.provenance import git_state

from .masking import Masker
from .profiles import ProviderProfile
from .questions import QUESTION_SETS, question_set_hashes
from .systemone import SystemOneAdapter
from .transport import BudgetExceeded, ReplayTransport, Transport

SCHEMA = "rosetta-bench/decision-eval@1"
THRESHOLDS = {"yes": 0.7, "no": 0.3}  # placeholders, not calibrated
POLICY = {"policy_id": "eval-placeholder", "version": "0.1", "calibrated": False}
OBJECTIVE = "Answer each question using only the evidence provided."
EVAL_ROUTE = RouteRef("evaluate", "Answer the listed questions about the evidence; no workflow is selected.",
                      hashlib.sha256(b"evaluate").hexdigest())
EVIDENCE_MAX_AGE = timedelta(days=1)
APPROVED_DATA_CLASSES = ("synthetic",)
_VERSIONED = re.compile(r"\d+\.\d+\.\d+")


@dataclass(frozen=True)
class EvalItem:
    item_id: str
    qset: str
    category: str
    language: str
    family: str
    subset: str | None
    data_class: str
    evidence: dict
    gold: dict
    unreviewed: dict


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _jsonl(text: str) -> list[dict]:
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def load_eval_corpus(corpus_dir: Path) -> tuple[list[EvalItem], str]:
    corpus_dir = Path(corpus_dir)
    items_text = (corpus_dir / "items.jsonl").read_text(encoding="utf-8")
    gold_text = (corpus_dir / "gold.jsonl").read_text(encoding="utf-8")
    gold = {row["item_id"]: row for row in _jsonl(gold_text)}
    items = []
    for raw in _jsonl(items_text):
        if raw["qset"] not in QUESTION_SETS:
            raise ValueError(f"{raw['item_id']}: unknown question set {raw['qset']!r}")
        label = gold.get(raw["item_id"])
        if label is None:
            raise ValueError(f"{raw['item_id']} has no gold record")
        qids = set(QUESTION_SETS[raw["qset"]].qids)
        if set(label["gold"]) != qids:
            raise ValueError(f"{raw['item_id']}: gold covers {sorted(label['gold'])}, question set has {sorted(qids)}")
        items.append(EvalItem(raw["item_id"], raw["qset"], raw["category"], raw["language"], raw.get("family", raw["item_id"]),
                              raw.get("subset"), raw.get("data_class", "synthetic"), raw["evidence"], label["gold"],
                              label.get("unreviewed", {})))
    digest = _sha(canonical_json({"items": items_text, "gold": gold_text, "questions": question_set_hashes()}))
    return items, digest


def noul_verdict(p) -> str:
    if p >= THRESHOLDS["yes"]:
        return "yes"
    if p <= THRESHOLDS["no"]:
        return "no"
    return "abstain"


def _judge(item: EvalItem, qset, result) -> tuple[dict, list[dict]]:
    """Per-question verdicts. A provider error or a violation on a question makes that question an error."""
    violations = [asdict(v) for v in validate_batch(result, qset)] if isinstance(result, AnswerBatch) else []
    bad = {v["qid"] for v in violations}
    judged: dict = {}
    for question in qset.questions:
        qid, gold = question.qid, item.gold[question.qid]
        entry: dict = {"primitive": question.primitive.value, "gold": gold}
        answer = result.answers.get(qid) if isinstance(result, AnswerBatch) else None
        if answer is None or qid in bad:
            entry["status"] = "error"
            entry["error"] = ("provider_error" if isinstance(result, ProviderError)
                              else next((v["code"] for v in violations if v["qid"] == qid), "MISSING"))
        elif question.primitive is Primitive.NOUL and isinstance(answer, NoulAnswer):
            verdict = noul_verdict(answer.p_yes)
            entry.update({"status": "answered", "p_yes": answer.p_yes, "verdict": verdict})
        elif question.primitive is Primitive.SCORE and isinstance(answer, ScoreAnswer):
            levels = question.levels
            index = min(len(levels) - 1, max(0, int(answer.position + 0.5)))
            entry.update({"status": "answered", "position": answer.position, "level": levels[index],
                          "probabilities": list(answer.probabilities) if answer.probabilities is not None else None,
                          "confidence": answer.confidence})
        else:
            entry.update({"status": "error", "error": "WRONG_PRIMITIVE"})
        if question.primitive is Primitive.NOUL:
            if entry["status"] == "answered" and entry["verdict"] != "abstain" and gold is not None:
                entry["correct"] = (entry["verdict"] == "yes") == gold
            else:
                entry["correct"] = None if gold is None else False
        judged[qid] = entry
    return judged, violations


def _outcome(item_state_ok: bool, result, judged: dict) -> tuple[str, list[str]]:
    if not item_state_ok:
        return "NEED_EVIDENCE", ["STATE_REJECTED"]
    if isinstance(result, ProviderError):
        return "FALLBACK", [f"PROVIDER_{result.kind.value}"]
    labelled = {qid: e for qid, e in judged.items() if e["primitive"] == "noul"}
    if any(e["status"] == "error" for e in labelled.values()):
        return "FALLBACK", [f"{qid}:INVALID" for qid, e in labelled.items() if e["status"] == "error"]
    codes = [f"{qid}:{e['verdict']}" for qid, e in labelled.items()]
    if any(e["verdict"] == "abstain" for e in labelled.values()):
        return "ABSTAIN", codes
    return "ACCEPT", codes


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
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def write_json(self, name: str, data: dict) -> None:
        (self.out / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def run_eval(
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
    item_ids: list[str] | None = None,
) -> Path:
    items, corpus_digest = load_eval_corpus(corpus_dir)
    if item_ids is not None:
        unknown = sorted(set(item_ids) - {item.item_id for item in items})
        if unknown:
            raise ValueError(f"unknown item ids: {unknown}")
        items = [item for item in items if item.item_id in set(item_ids)]
    model = model or profile.default_model
    expected_served = profile.expected_served_model or model
    now = datetime.fromisoformat(state_time) if state_time else datetime.now(timezone.utc).replace(microsecond=0)
    order = [item.item_id for item in items]
    random.Random(seed).shuffle(order)
    by_id = {item.item_id: item for item in items}
    run_id = f"eval-{uuid.uuid4().hex[:12]}"
    repos = {"core": _repo_state(rosetta_core), "bench": _repo_state(rosetta_bench)}

    writer = _Writer(out_dir)
    manifest = {
        "schema": SCHEMA,
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "corpus_dir": str(Path(corpus_dir).resolve()),
        "corpus_digest": corpus_digest,
        "item_filter": sorted(item_ids) if item_ids is not None else None,
        "provider": {"profile": profile.name, "endpoint": profile.endpoint, "requested_model": model,
                     "expected_served_model": expected_served, "notes": profile.notes},
        "synthetic": profile.name.startswith("fake"),
        "live": live,
        "seed": seed,
        "order": order,
        "state_time": now.isoformat(),
        "question_sets": {name: {"set_id": q.set_id, "version": q.version, "hash": q.content_hash(), "qids": list(q.qids)}
                          for name, q in QUESTION_SETS.items()},
        "policy": {**POLICY, "thresholds": THRESHOLDS},
        "max_transport_retries": max_transport_retries,
        "repos": repos,
        "environment": {"python": sys.version.split()[0], "platform": platform.platform()},
        "stopped_early": None,
    }
    writer.write_json("manifest.json", manifest)

    adapter = SystemOneAdapter(profile, transport, model=model, api_key=api_key, max_transport_retries=max_transport_retries)
    forbidden_extra = (api_key,) if api_key else ()
    for item_id in order:
        item = by_id[item_id]
        qset = QUESTION_SETS[item.qset]
        masker = Masker()
        evidence = tuple(Evidence(key, masker.mask_value(value), f"corpus:{item.item_id}", now.isoformat())
                         for key, value in item.evidence.items())
        required = sorted({path.removeprefix("evidence.") for q in qset.questions for path in q.required_state_paths})
        state, state_problem = None, None
        if item.data_class not in APPROVED_DATA_CLASSES:
            state_problem = [f"DATA_CLASS_NOT_APPROVED:{item.data_class}"]
        else:
            try:
                state = build_state(
                    request_id=item.item_id, objective=OBJECTIVE, constraints={"data_class": item.data_class},
                    evidence=evidence, eligible_routes=(EVAL_ROUTE,), policy_ref=f"{POLICY['policy_id']}@{POLICY['version']}",
                    required=tuple(required), max_age={key: EVIDENCE_MAX_AGE for key in item.evidence}, now=now,
                )
            except StateRejected as rejected:
                state_problem = list(rejected.missing + rejected.stale + rejected.problems)

        ask = None
        if state is not None:
            try:
                ask = adapter.ask(wire_state(state), qset, context={"case_id": item.item_id})
            except BudgetExceeded as exc:
                manifest["stopped_early"] = str(exc)
                break
            for exchange in ask.exchanges:
                assert_no_secrets(exchange, forbidden=masker.originals + forbidden_extra)
                writer.append("exchanges.jsonl", exchange)
        result = ask.result if ask else None
        judged, violations = _judge(item, qset, result)
        outcome, reason_codes = _outcome(state is not None, result, judged)
        served = result.served_model if isinstance(result, AnswerBatch) else None
        decision = {
            "item_id": item.item_id, "qset": item.qset, "category": item.category, "language": item.language,
            "family": item.family, "subset": item.subset, "outcome": outcome, "reason_codes": reason_codes,
            "questions": judged, "unreviewed": item.unreviewed, "violations": violations, "state_problems": state_problem,
            "provider_error": {"kind": result.kind.value, "detail": result.detail} if isinstance(result, ProviderError) else None,
            "unmapped_scores": result.extras.get("unmapped_scores", []) if isinstance(result, AnswerBatch) else [],
            "served_model": served, "served_matches_expected": None if served is None else served == expected_served,
            "input_tokens": ask.input_tokens if ask else None, "calls": ask.calls if ask else 0,
            "transport_retries": ask.transport_retries if ask else 0, "decision_ms": ask.elapsed_ms if ask else 0.0,
        }
        receipt = {
            "receipt_version": RECEIPT_VERSION, "receipt_id": new_receipt_id(), "run_id": run_id,
            "trial_id": f"{run_id}:{item.item_id}", "case_id": item.item_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "repos": {name: (state_ or {}).get("sha") for name, state_ in repos.items()},
            "contract_version": CONTRACT_VERSION,
            "state": {"schema_version": STATE_SCHEMA_VERSION,
                      "digest": state_digest(state) if state else _sha(item.item_id),
                      "snapshot_ref": f"exchanges.jsonl#{item.item_id}" if ask and ask.exchanges else None},
            "replay": "available" if ask and ask.exchanges else "unavailable",
            "question_set": {"set_id": qset.set_id, "version": qset.version, "hash": qset.content_hash()},
            "policy": dict(POLICY),
            "provider": {"name": profile.name, "requested_model": model, "served_model": served,
                         "revision_known": bool(served and served == expected_served
                                                and (profile.pins_versions or _VERSIONED.search(served)))},
            "answers_ref": f"decisions.jsonl#{item.item_id}",
            "recommendation": {"outcome": outcome, "route": None, "reason_codes": reason_codes},
            "executed_route": None,
            "mode": "shadow",
            "generator": None,
            "usage": {"decision_input_tokens": ask.input_tokens if ask else 0},
            "cost": estimate_cost_v2(profile.pricing_tool, model, ask.input_tokens if ask else 0, 0).to_dict(),
            "timings_ms": {"decision": ask.elapsed_ms if ask else 0.0},
            "retries": {"transport": ask.transport_retries if ask else 0, "semantic": 0},
            "output_digest": None,
            "outcome": {"verified_success": None,
                        "checks": {f"{qid}_matches_gold": e.get("correct") for qid, e in judged.items() if e["primitive"] == "noul"}},
            "override": None,
        }
        validate_receipt(receipt)
        assert_no_secrets(receipt, forbidden=masker.originals + forbidden_extra)
        assert_no_secrets(decision, forbidden=masker.originals + forbidden_extra)
        writer.append("decisions.jsonl", decision)
        writer.append("receipts.jsonl", receipt)
    writer.write_json("manifest.json", manifest)
    return writer.out


def is_eval_run(run_dir: Path) -> bool:
    path = Path(run_dir) / "manifest.json"
    return path.exists() and json.loads(path.read_text(encoding="utf-8")).get("schema") == SCHEMA


@dataclass
class EvalReplayReport:
    items: int
    mismatches: list[str]


def _lines(path: Path) -> list[dict]:
    return _jsonl(path.read_text(encoding="utf-8")) if path.exists() else []


def _comparable(decision: dict) -> dict:
    return {"outcome": decision["outcome"], "reason_codes": decision["reason_codes"],
            "questions": {qid: {k: e.get(k) for k in ("status", "verdict", "p_yes", "position", "error")}
                          for qid, e in decision["questions"].items()}}


def replay_eval(run_dir: Path, profiles: dict | None = None) -> EvalReplayReport:
    from .profiles import PROFILES

    run_dir = Path(run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    corpus_dir = Path(manifest["corpus_dir"])
    _, digest = load_eval_corpus(corpus_dir)
    if digest != manifest["corpus_digest"]:
        raise ValueError("corpus or question sets changed since the run; replay would not be like for like")
    profile = (profiles or PROFILES)[manifest["provider"]["profile"]]
    profile = replace(profile, expected_served_model=manifest["provider"].get("expected_served_model"))
    original = {d["item_id"]: d for d in _lines(run_dir / "decisions.jsonl")}
    exchanges = _lines(run_dir / "exchanges.jsonl")
    with tempfile.TemporaryDirectory(prefix="rosetta-eval-replay-") as tmp:
        replayed_dir = run_eval(
            corpus_dir, profile, ReplayTransport(exchanges), Path(tmp) / "replay", seed=manifest["seed"],
            api_key=f"no-key-{uuid.uuid4().hex}" if profile.api_key_env else None, state_time=manifest["state_time"],
            model=manifest["provider"]["requested_model"], max_transport_retries=manifest["max_transport_retries"],
            item_ids=[item_id for item_id in manifest["order"] if item_id in original],
        )
        replayed = {d["item_id"]: d for d in _lines(replayed_dir / "decisions.jsonl")}
    mismatches = sorted(item_id for item_id, decision in original.items()
                        if item_id not in replayed or _comparable(decision) != _comparable(replayed[item_id]))
    return EvalReplayReport(items=len(original), mismatches=mismatches)
