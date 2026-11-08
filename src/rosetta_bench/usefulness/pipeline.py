"""Paired usefulness arms over the same tasks, in a seeded random order.

  A  HUMAN route contract, no decision layer (baseline route for every request)
  B  MACHINE route contract, no decision layer
  C  MACHINE + intake decision, enforced: ACCEPT uses the chosen route's contract,
     NO_FIT/DENY decline without generating, ABSTAIN/FALLBACK/NEED_EVIDENCE fall back
     to the baseline route. Optional postflight is advisory only.

Success: a code task passes its hidden tests in the sandbox; a no-code task produces
no code (declined by the decision layer, or the generator answered without code).
"""
from __future__ import annotations

import hashlib
import json
import platform
import random
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
    Outcome,
    RouteRef,
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
from rosetta_bench.decision.battery import intake_battery, postflight_battery
from rosetta_bench.decision.masking import Masker
from rosetta_bench.decision.shadow import placeholder_policy
from rosetta_bench.decision.systemone import SystemOneAdapter
from rosetta_bench.decision.transport import BudgetExceeded
from rosetta_bench.models import RunResult, Task
from rosetta_bench.pricing import estimate_cost_v2
from rosetta_bench.provenance import git_state
from rosetta_bench.timing import StageTimer

from .corpus import UsefulnessTask, corpus_digest, hidden_tests, load_tasks, route_contract, route_ids
from .extract import extract_code, says_not_applicable

BASELINE_ROUTE = "code_change"
SANDBOX_FACTORY = None  # tests replace this with a fake; None means the real Docker sandbox


@dataclass(frozen=True)
class ArmSpec:
    arm_id: str
    prompt_format: str
    routing: bool
    postflight: bool


def arm_specs(arm_ids: list[str], postflight: bool) -> list[ArmSpec]:
    library = {
        "A": ArmSpec("A", "HUMAN", False, False),
        "B": ArmSpec("B", "MACHINE", False, False),
        "C": ArmSpec("C", "MACHINE", True, postflight),
    }
    unknown = [a for a in arm_ids if a not in library]
    if unknown:
        raise ValueError(f"unknown arms {unknown}; choose from {sorted(library)}")
    return [library[a] for a in arm_ids]


class GeneratorBudgetExceeded(Exception):
    pass


class BudgetedGenerator:
    def __init__(self, inner, max_calls: int | None):
        self.inner = inner
        self.name = inner.name
        self.model = inner.model
        self.max_calls = max_calls
        self.calls = 0

    def run(self, prompt_text: str, task: Task | None) -> RunResult:
        if self.max_calls is not None and self.calls >= self.max_calls:
            raise GeneratorBudgetExceeded(f"generator budget of {self.max_calls} calls reached")
        self.calls += 1
        return self.inner.run(prompt_text, task)


class FakeCodeGenerator:
    """SYNTHETIC offline coder: returns the reference solution for code tasks under the
    code_change contract (deliberately broken for some), prose under other contracts,
    NOT_A_CODE_TASK for no-code requests (but code for one of them)."""

    name = "FAKE"
    model = "fake-coder-1"

    def __init__(self, corpus_dir: Path, broken=("u04",), codes_anyway=("u14",)):
        self.corpus_dir = Path(corpus_dir)
        self.tasks = {t.task_id: t for t in load_tasks(corpus_dir)}
        self.broken = set(broken)
        self.codes_anyway = set(codes_anyway)

    def run(self, prompt_text: str, task: Task | None) -> RunResult:
        item = self.tasks[task.name]
        if "code_change" not in prompt_text:
            output = "Here is the revised text, as requested."
        elif item.kind == "no_code":
            output = "```python\ndef answer():\n    return 'done'\n```" if item.task_id in self.codes_anyway else "NOT_A_CODE_TASK"
        elif item.task_id in self.broken:
            output = f"```python\n# BROKEN\ndef {item.entry_point}(*args):\n    raise NotImplementedError\n```"
        else:
            reference = (self.corpus_dir / "reference" / f"{item.task_id}.py").read_text(encoding="utf-8")
            output = f"```python\n{reference}```"
        sent = f"{prompt_text}\n\nTask: {task.instructions}"
        return RunResult(raw_output=output, tokens_in=len(sent.split()), tokens_out=len(output.split()), latency_ms=0.0)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _repo(module) -> dict | None:
    return git_state(Path(module.__file__).resolve().parents[2])


def _append(path: Path, record: dict) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, allow_nan=True) + "\n")


def run_usefulness(
    corpus_dir: Path,
    arms: list[ArmSpec],
    generator,
    generator_meta: dict,
    out_dir: Path,
    *,
    seed: int,
    live: bool,
    decision=None,  # (profile, transport, api_key) or None
    sandbox=None,
) -> Path:
    corpus_dir = Path(corpus_dir)
    out_dir = Path(out_dir)
    if (out_dir / "manifest.json").exists():
        raise FileExistsError(f"a run already exists in {out_dir}; choose a new --out directory")
    if any(arm.routing for arm in arms) and decision is None:
        raise ValueError("arm C needs a decision provider (--decision)")
    if sandbox is None:
        from rosetta_bench.sandbox import DockerSandbox

        sandbox = SANDBOX_FACTORY() if SANDBOX_FACTORY else DockerSandbox()

    tasks = load_tasks(corpus_dir)
    routes = [{"id": rid, "description": route_contract(corpus_dir, rid, "MACHINE")} for rid in route_ids(corpus_dir)]
    route_descriptions = json.loads((corpus_dir.parent / "routing_smoke" / "routes.json").read_text(encoding="utf-8"))["routes"]
    descriptions = {r["id"]: r["description"] for r in route_descriptions}
    catalogue = [{"id": r["id"], "description": descriptions.get(r["id"], r["id"])} for r in routes]
    intake = intake_battery(catalogue)
    postflight = postflight_battery()
    route_refs = tuple(RouteRef(r["id"], r["description"], _sha(canonical_json(r))) for r in catalogue)

    adapter = policy = None
    profile = None
    api_key = None
    if decision is not None:
        profile, transport, api_key = decision
        adapter = SystemOneAdapter(profile, transport, api_key=api_key)
        policy = placeholder_policy(profile, profile.expected_served_model or profile.default_model, intake)

    plan = [(arm, task) for arm in arms for task in tasks]
    random.Random(seed).shuffle(plan)
    run_id = f"use-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).replace(microsecond=0)
    repos = {"core": _repo(rosetta_core), "bench": _repo(rosetta_bench)}
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": "rosetta-bench/usefulness-run@1",
        "run_id": run_id,
        "created_at": now.isoformat(),
        "corpus_dir": str(corpus_dir.resolve()),
        "corpus_digest": corpus_digest(corpus_dir),
        "arms": [asdict(arm) for arm in arms],
        "generator": generator_meta,
        "decision": None if profile is None else {
            "profile": profile.name, "requested_model": profile.default_model,
            "expected_served_model": profile.expected_served_model,
            "intake_question_set": {"version": intake.version, "hash": intake.content_hash()},
            "postflight_question_set": {"version": postflight.version, "hash": postflight.content_hash()},
            "policy": {"policy_id": policy.policy_id, "version": policy.version, "calibrated": policy.calibrated},
        },
        "synthetic": generator_meta["kind"] == "fake" and (profile is None or profile.name == "fake"),
        "live": live,
        "seed": seed,
        "order": [f"{arm.arm_id}:{task.task_id}" for arm, task in plan],
        "repos": repos,
        "environment": {"python": sys.version.split()[0], "platform": platform.platform()},
        "stopped_early": None,
        "notes": "Postflight is advisory. Tasks are the unit of paired comparison; repeats are not new tasks.",
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    forbidden = (api_key,) if api_key else ()

    for arm, task in plan:
        timer = StageTimer()
        with timer.stage("total"):
            try:
                record = _trial(arm, task, corpus_dir, generator, sandbox, adapter, policy, intake, postflight,
                                route_refs, now, timer, out_dir, forbidden)
            except (GeneratorBudgetExceeded, BudgetExceeded) as exc:
                manifest["stopped_early"] = str(exc)
                break
        record["timings_ms"] = dict(timer.timings_ms)
        record.update({"run_id": run_id, "arm": arm.arm_id, "prompt_format": arm.prompt_format, "task_id": task.task_id,
                       "kind": task.kind, "language": task.language, "synthetic": manifest["synthetic"]})
        record["generator_cost"] = estimate_cost_v2(generator.name, generator.model,
                                                    record["generator_tokens_in"], record["generator_tokens_out"]).to_dict()
        record["decision_cost"] = (estimate_cost_v2(profile.pricing_tool, profile.default_model, record["decision_tokens"], 0).to_dict()
                                   if arm.routing else None)
        assert_no_secrets(record, forbidden=forbidden)
        _append(out_dir / "trials.jsonl", record)
        if arm.routing:
            receipt = _receipt(record, run_id, repos, intake, policy, profile, generator, arm)
            validate_receipt(receipt)
            assert_no_secrets(receipt, forbidden=forbidden)
            _append(out_dir / "receipts.jsonl", receipt)
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return out_dir


def _ask(adapter, qset, task, now, route_refs, proposed_output, context, out_dir, forbidden):
    masker = Masker()
    state = build_state(
        request_id=task.task_id, objective="Choose the workflow for this request, or judge the proposed output.",
        constraints={"data_class": "synthetic"},
        evidence=(Evidence("request.text", masker.mask_value(task.request_text), f"corpus:{task.task_id}", now.isoformat()),),
        eligible_routes=route_refs, policy_ref="usefulness", required=("request.text",),
        max_age={"request.text": timedelta(days=1)}, now=now, proposed_output=proposed_output, max_bytes=400_000,
    )
    ask = adapter.ask(wire_state(state), qset, context=context)
    for exchange in ask.exchanges:
        assert_no_secrets(exchange, forbidden=masker.originals + forbidden)
        _append(out_dir / "exchanges.jsonl", exchange)
    return state, ask


def _trial(arm, task: UsefulnessTask, corpus_dir, generator, sandbox, adapter, policy, intake, postflight,
           route_refs, now, timer, out_dir, forbidden) -> dict:
    record = {
        "route_decision": None, "route": BASELINE_ROUTE, "declined_by": None, "generated": False,
        "generator_tokens_in": 0, "generator_tokens_out": 0, "decision_tokens": 0, "decision_calls": 0,
        "code_extracted": False, "sandbox": None, "success": False, "postflight": None, "error": None,
        "output_digest": None, "state_digest": None, "raw_output": None,
    }
    context = {"task_id": task.task_id, "arm": arm.arm_id}
    if arm.routing:
        with timer.stage("decision"):
            state, ask = _ask(adapter, intake, task, now, route_refs, None, {**context, "stage": "intake"}, out_dir, forbidden)
            recommendation = reduce(GateResult(eligible_routes=tuple(r.route_id for r in route_refs)), ask.result, policy, intake)
        record["state_digest"] = state_digest(state)
        record["decision_tokens"] += ask.input_tokens or 0
        record["decision_calls"] += ask.calls
        record["route_decision"] = {"outcome": recommendation.outcome.value, "route": recommendation.route,
                                    "reason_codes": list(recommendation.reason_codes), "signals": dict(recommendation.signals),
                                    "served_model": ask.result.served_model if isinstance(ask.result, AnswerBatch) else None}
        if recommendation.outcome in (Outcome.NO_FIT, Outcome.DENY):
            record["route"], record["declined_by"] = None, "decision"
        elif recommendation.outcome is Outcome.ACCEPT:
            record["route"] = recommendation.route

    output = None
    if record["route"] is not None:
        contract = route_contract(corpus_dir, record["route"], arm.prompt_format)
        try:
            with timer.stage("generation"):
                result = generator.run(contract, Task(name=task.task_id, instructions=task.request_text))
        except (GeneratorBudgetExceeded, BudgetExceeded):
            raise
        except Exception as exc:  # a failed generation is a recorded failure
            record["error"] = f"generation: {type(exc).__name__}: {exc}"[:300]
            return record
        record["generated"] = True
        output = result.raw_output
        record["generator_tokens_in"], record["generator_tokens_out"] = result.tokens_in, result.tokens_out
        record["raw_output"] = output
        record["output_digest"] = _sha(output)

    code = extract_code(output)
    record["code_extracted"] = code is not None
    if task.kind == "code":
        if code is not None:
            with timer.stage("sandbox"):
                result = sandbox.run_tests({"solution.py": code, "test_task.py": hidden_tests(corpus_dir, task)})
            record["sandbox"] = {"passed": result.passed, "tests_run": result.tests_run, "failures": result.failures,
                                 "timed_out": result.timed_out}
            record["success"] = result.passed
    else:
        record["success"] = code is None
        if output is not None and says_not_applicable(output):
            record["declined_by"] = "generator"

    if arm.postflight and code is not None and adapter is not None:
        with timer.stage("postflight"):
            _, ask = _ask(adapter, postflight, task, now, route_refs, code[:8000], {**context, "stage": "postflight"}, out_dir, forbidden)
        record["decision_tokens"] += ask.input_tokens or 0
        record["decision_calls"] += ask.calls
        valid = isinstance(ask.result, AnswerBatch) and not validate_batch(ask.result, postflight)
        record["postflight"] = {"addresses_task": ask.result.answers["addresses_task"].p_yes if valid else None,
                                "error": None if valid else "invalid or failed postflight answer"}
    return record


def _receipt(record, run_id, repos, intake, policy, profile, generator, arm) -> dict:
    decision = record["route_decision"]
    served = decision["served_model"]
    return {
        "receipt_version": RECEIPT_VERSION, "receipt_id": new_receipt_id(), "run_id": run_id,
        "trial_id": f"{run_id}:{arm.arm_id}:{record['task_id']}", "case_id": record["task_id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "repos": {name: (state or {}).get("sha") for name, state in repos.items()},
        "contract_version": CONTRACT_VERSION,
        "state": {"schema_version": STATE_SCHEMA_VERSION, "digest": record["state_digest"], "snapshot_ref": f"exchanges.jsonl#{record['task_id']}"},
        "replay": "available",
        "question_set": {"set_id": intake.set_id, "version": intake.version, "hash": intake.content_hash()},
        "policy": {"policy_id": policy.policy_id, "version": policy.version, "calibrated": policy.calibrated},
        "provider": {"name": profile.name, "requested_model": profile.default_model, "served_model": served,
                     "revision_known": bool(served and served == profile.expected_served_model and any(c.isdigit() for c in served))},
        "answers_ref": f"trials.jsonl#{arm.arm_id}:{record['task_id']}",
        "recommendation": {"outcome": decision["outcome"], "route": decision["route"], "reason_codes": decision["reason_codes"]},
        "executed_route": record["route"],
        "mode": "enforced",
        "generator": {"tool": generator.name, "model": generator.model, "settings": {}},
        "usage": {"decision_input_tokens": record["decision_tokens"], "generator_tokens_in": record["generator_tokens_in"],
                  "generator_tokens_out": record["generator_tokens_out"]},
        "cost": record["decision_cost"],
        "timings_ms": record["timings_ms"],
        "retries": {"transport": 0, "semantic": 0},
        "output_digest": record["output_digest"],
        "outcome": {"verified_success": record["success"],
                    "checks": {"acceptance_tests": record["sandbox"]["passed"] if record["sandbox"] else None,
                               "no_code_produced": (not record["code_extracted"]) if record["kind"] == "no_code" else None}},
        "override": None,
    }
