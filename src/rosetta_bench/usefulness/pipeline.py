"""Representation x decision matrix over bounded coding tasks.

Representations (generator prompt):  P plain prose | H Rosetta .md | M Rosetta .cpn
Deciders:  none | <provider profile> (e.g. jevmodel, clef-ollama) | consensus (all providers in the run)

Phase 1 - decisions: each provider judges each task once (the decision state is the request
  only, so representation and decision effects stay separable).
Phase 2 - arms: route from the decider (none -> baseline). NO_FIT/DENY decline without
  generating; ACCEPT uses the chosen route's contract; anything else falls back to the
  baseline route. Identical prompts share one generation and identical code shares one
  sandbox run; every arm is charged the original call's tokens and time.
Phase 3 - advisory postflight on generated code for the requested representations.

Success is decided per task kind by the verifier registry in verify.py: code tasks pass their
hidden tests in the sandbox; no-code tasks produce no code; v2 kinds (docs_edit, translation_review,
data_query, clarify, unsolvable, false_premise) have their own deterministic checks. The route used
without a decision layer (and on fallback) is the corpus's baseline route (corpus.json; default
code_change).
"""
from __future__ import annotations

import hashlib
import json
import platform
import random
import sys
import uuid
from dataclasses import dataclass
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
    Recommendation,
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

from .corpus import REPRESENTATIONS, UsefulnessTask, corpus_config, corpus_digest, load_tasks, route_contract, route_ids
from .extract import extract_code, says_not_applicable
from .reason_first import HANDOFF_VERDICTS, PLAN_SCHEMA_VER, PLANNER_PROMPT, PlanError, execution_prompt, non_proceed_output, parse_plan
from .verify import VerifyContext, verify

BASELINE_ROUTE = "code_change"
SANDBOX_FACTORY = None  # tests replace this with a fake; None means the real Docker sandbox
NO_DECIDER = "none"
CONSENSUS = "consensus"
REASON_FIRST = "R"


@dataclass(frozen=True)
class Arm:
    rep: str
    decider: str

    @property
    def arm_id(self) -> str:
        return f"{self.rep}+{self.decider}"


def consensus(recommendations: list[Recommendation]) -> Recommendation:
    """Any DENY wins; ACCEPT only if every provider accepts the same route; NO_FIT only if
    every provider says no-fit; anything else abstains (and so falls back)."""
    outcomes = [r.outcome for r in recommendations]
    if Outcome.DENY in outcomes:
        return Recommendation(Outcome.DENY, None, ("CONSENSUS_DENY",))
    routes = {r.route for r in recommendations}
    if all(o is Outcome.ACCEPT for o in outcomes) and len(routes) == 1:
        return Recommendation(Outcome.ACCEPT, routes.pop(), ("CONSENSUS_ACCEPT",))
    if all(o is Outcome.NO_FIT for o in outcomes):
        return Recommendation(Outcome.NO_FIT, None, ("CONSENSUS_NO_FIT",))
    return Recommendation(Outcome.ABSTAIN, None, ("NO_CONSENSUS",))


class GeneratorBudgetExceeded(Exception):
    pass


class BudgetedGenerator:
    def __init__(self, inner, max_calls: int | None):
        self.inner, self.name, self.model = inner, inner.name, inner.model
        self.max_calls = max_calls
        self.calls = 0

    def run(self, prompt_text: str, task: Task | None) -> RunResult:
        if self.max_calls is not None and self.calls >= self.max_calls:
            raise GeneratorBudgetExceeded(f"generator budget of {self.max_calls} calls reached")
        self.calls += 1
        return self.inner.run(prompt_text, task)


class FakeCodeGenerator:
    """SYNTHETIC offline coder: reference solutions under a code-capable contract (broken
    for some tasks), prose under other contracts, NOT_A_CODE_TASK for no-code requests
    (but code for one of them). For the other kinds it replays the corpus's reference reply
    (reference/<id>.md); `refuses` answers UNSOLVABLE instead and `cheats` returns an
    always-equal object (a gamed "Kirk" solution). Not a model."""

    name = "FAKE"
    model = "fake-coder-1"

    def __init__(self, corpus_dir: Path, broken=("u04",), codes_anyway=("u14",), refuses=(), cheats=()):
        self.corpus_dir = Path(corpus_dir)
        self.tasks = {t.task_id: t for t in load_tasks(corpus_dir)}
        self.broken, self.codes_anyway = set(broken), set(codes_anyway)
        self.refuses, self.cheats = set(refuses), set(cheats)

    def run(self, prompt_text: str, task: Task | None) -> RunResult:
        item = self.tasks[task.name]
        reference = self.corpus_dir / "reference" / f"{item.task_id}.md"
        code_capable = "code_change" in prompt_text or "NOT_A_CODE_TASK" in prompt_text or "python" in prompt_text.lower()
        if item.task_id in self.refuses:
            output = "UNSOLVABLE: these requirements cannot all be met together."
        elif item.task_id in self.cheats:
            output = (f"```python\nclass _Always:\n    def __eq__(self, other):\n        return True\n\n"
                      f"    def __getitem__(self, key):\n        return self\n\n\ndef {item.entry_point}(*args, **kwargs):\n"
                      f"    return _Always()\n```")
        elif item.kind not in ("code", "no_code") and reference.exists():
            output = reference.read_text(encoding="utf-8")
        elif not code_capable:
            output = "Here is the revised text, as requested."
        elif item.kind == "no_code":
            output = "```python\ndef answer():\n    return 'done'\n```" if item.task_id in self.codes_anyway else "NOT_A_CODE_TASK"
        elif item.task_id in self.broken:
            output = f"```python\n# BROKEN\ndef {item.entry_point}(*args):\n    raise NotImplementedError\n```"
        else:
            output = f"```python\n{(self.corpus_dir / 'reference' / f'{item.task_id}.py').read_text(encoding='utf-8')}```"
        sent = f"{prompt_text}\n\nTask: {task.instructions}"
        return RunResult(raw_output=output, tokens_in=len(sent.split()), tokens_out=len(output.split()), latency_ms=0.0)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _repo(module) -> dict | None:
    return git_state(Path(module.__file__).resolve().parents[2])


def _append(path: Path, record: dict) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, allow_nan=True) + "\n")


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


class _Context:
    def __init__(self, corpus_dir: Path, out_dir: Path, providers: dict, forbidden: tuple):
        self.corpus_dir, self.out_dir, self.forbidden = corpus_dir, out_dir, forbidden
        self.tasks = load_tasks(corpus_dir)
        self.config = corpus_config(corpus_dir)
        self.baseline_route = self.config["baseline_route"]
        catalogue_source = json.loads((corpus_dir.parent / "routing_smoke" / "routes.json").read_text(encoding="utf-8"))["routes"]
        descriptions = {r["id"]: r["description"] for r in catalogue_source}
        self.catalogue = [{"id": rid, "description": descriptions.get(rid, rid)} for rid in route_ids(corpus_dir)
                          if rid not in self.config["catalogue_exclude"]]
        self.intake = intake_battery(self.catalogue)
        self.postflight = postflight_battery()
        self.route_refs = tuple(RouteRef(r["id"], r["description"], _sha(canonical_json(r))) for r in self.catalogue)
        self.now = datetime.now(timezone.utc).replace(microsecond=0)
        self.providers = {}
        for name, (profile, transport, key) in providers.items():
            adapter = SystemOneAdapter(profile, transport, api_key=key)
            policy = placeholder_policy(profile, profile.expected_served_model or profile.default_model, self.intake)
            self.providers[name] = (profile, adapter, policy)

    def ask(self, provider: str, qset, task: UsefulnessTask, proposed_output, stage: str):
        profile, adapter, _ = self.providers[provider]
        masker = Masker()
        state = build_state(
            request_id=task.task_id, objective="Choose the workflow for this request, or judge the proposed output.",
            constraints={"data_class": "synthetic"},
            evidence=(Evidence("request.text", masker.mask_value(task.request_text), f"corpus:{task.task_id}", self.now.isoformat()),),
            eligible_routes=self.route_refs, policy_ref="usefulness", required=("request.text",),
            max_age={"request.text": timedelta(days=1)}, now=self.now, proposed_output=proposed_output, max_bytes=400_000,
        )
        ask = adapter.ask(wire_state(state), qset, context={"task_id": task.task_id, "provider": provider, "stage": stage})
        for exchange in ask.exchanges:
            assert_no_secrets(exchange, forbidden=masker.originals + self.forbidden)
            _append(self.out_dir / "exchanges.jsonl", exchange)
        return state, ask


def run_matrix(
    corpus_dir: Path,
    reps: list[str],
    deciders: list[str],
    generator,
    generator_meta: dict,
    out_dir: Path,
    *,
    seed: int,
    live: bool,
    providers: dict | None = None,  # name -> (profile, transport, api_key)
    postflight_reps: tuple[str, ...] = (),
    sandbox=None,
    planner=None,
    planner_meta: dict | None = None,
) -> Path:
    corpus_dir, out_dir = Path(corpus_dir), Path(out_dir)
    providers = providers or {}
    if REASON_FIRST in reps and planner is None:
        raise ValueError("representation R (reason-first) needs a planner")
    if (out_dir / "manifest.json").exists():
        raise FileExistsError(f"a run already exists in {out_dir}; choose a new --out directory")
    unknown_reps = [r for r in reps if r not in REPRESENTATIONS]
    if unknown_reps:
        raise ValueError(f"unknown representations {unknown_reps}; choose from {sorted(REPRESENTATIONS)}")
    provider_deciders = [d for d in deciders if d not in (NO_DECIDER, CONSENSUS)]
    missing = [d for d in provider_deciders if d not in providers]
    if missing:
        raise ValueError(f"no provider configured for deciders {missing}")
    if CONSENSUS in deciders and len(provider_deciders) < 2:
        raise ValueError("consensus needs at least two provider deciders in the same run")
    if sandbox is None:
        from rosetta_bench.sandbox import DockerSandbox

        sandbox = SANDBOX_FACTORY() if SANDBOX_FACTORY else DockerSandbox()

    api_keys = tuple(key for (_, _, key) in providers.values() if key)
    ctx = _Context(corpus_dir, out_dir, {name: providers[name] for name in provider_deciders}, api_keys)
    arms = [Arm(rep, decider) for rep in reps for decider in deciders]
    plan = [(arm, task) for arm in arms for task in ctx.tasks]
    random.Random(seed).shuffle(plan)
    run_id = f"use-{uuid.uuid4().hex[:12]}"
    repos = {"core": _repo(rosetta_core), "bench": _repo(rosetta_bench)}
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": "rosetta-bench/usefulness-matrix@1",
        "run_id": run_id,
        "created_at": ctx.now.isoformat(),
        "corpus_dir": str(corpus_dir.resolve()),
        "corpus_digest": corpus_digest(corpus_dir),
        "representations": {rep: REPRESENTATIONS[rep] for rep in reps},
        "baseline_route": ctx.baseline_route,
        "deciders": deciders,
        "arms": [arm.arm_id for arm in arms],
        "generator": generator_meta,
        "planner": planner_meta if REASON_FIRST in reps else None,
        "providers": {
            name: {"profile": profile.name, "requested_model": profile.default_model,
                   "expected_served_model": profile.expected_served_model,
                   "policy": {"policy_id": policy.policy_id, "version": policy.version, "calibrated": policy.calibrated}}
            for name, (profile, _, policy) in ctx.providers.items()
        },
        "question_sets": {"intake": {"version": ctx.intake.version, "hash": ctx.intake.content_hash()},
                          "postflight": {"version": ctx.postflight.version, "hash": ctx.postflight.content_hash()}},
        "postflight_reps": list(postflight_reps),
        "synthetic": generator_meta["kind"] == "fake" and all(p.pricing_tool == "FAKE" for p, _, _ in ctx.providers.values()),
        "live": live,
        "seed": seed,
        "order": [f"{arm.arm_id}:{task.task_id}" for arm, task in plan],
        "repos": repos,
        "environment": {"python": sys.version.split()[0], "platform": platform.platform()},
        "accounting": "Identical prompts share one generation and identical code one sandbox run; each arm is charged "
                      "the original call's tokens and time. Decisions are made once per provider and task.",
        "stopped_early": None,
    }
    _write_json(out_dir / "manifest.json", manifest)

    try:
        decisions = _decide_all(ctx, provider_deciders, seed)
        generations: dict[str, dict] = {}
        sandboxes: dict[str, dict] = {}
        postflights: dict[tuple[str, str], dict] = {}
        for arm, task in plan:
            record = _arm_trial(ctx, arm, task, decisions, provider_deciders, generator, sandbox,
                                generations, sandboxes, postflights, postflight_reps, planner=planner)
            record.update({"run_id": run_id, "synthetic": manifest["synthetic"]})
            assert_no_secrets(record, forbidden=api_keys)
            _append(out_dir / "trials.jsonl", record)
            if arm.decider != NO_DECIDER:
                receipt = _receipt(ctx, record, run_id, repos, arm, generator, decisions, provider_deciders)
                validate_receipt(receipt)
                assert_no_secrets(receipt, forbidden=api_keys)
                _append(out_dir / "receipts.jsonl", receipt)
    except (GeneratorBudgetExceeded, BudgetExceeded) as exc:
        manifest["stopped_early"] = str(exc)
    _write_json(out_dir / "manifest.json", manifest)
    return out_dir


def _decide_all(ctx: _Context, provider_deciders: list[str], seed: int) -> dict:
    decisions: dict[tuple[str, str], dict] = {}
    for provider in provider_deciders:
        profile, _, policy = ctx.providers[provider]
        order = list(ctx.tasks)
        random.Random(f"{seed}:{provider}").shuffle(order)
        for task in order:
            state, ask = ctx.ask(provider, ctx.intake, task, None, "intake")
            gates = GateResult(eligible_routes=tuple(r.route_id for r in ctx.route_refs))
            rec = reduce(gates, ask.result, policy, ctx.intake)
            record = {
                "provider": provider, "task_id": task.task_id, "kind": task.kind, "language": task.language,
                "expected_route": task.expected_route, "outcome": rec.outcome.value, "route": rec.route,
                "reason_codes": list(rec.reason_codes), "signals": dict(rec.signals),
                "served_model": ask.result.served_model if isinstance(ask.result, AnswerBatch) else None,
                "provider_error": None if isinstance(ask.result, AnswerBatch) else {"kind": ask.result.kind.value, "detail": ask.result.detail},
                "input_tokens": ask.input_tokens or 0, "calls": ask.calls, "decision_ms": ask.elapsed_ms,
                "transport_retries": ask.transport_retries,
                "state_digest": state_digest(state),
            }
            assert_no_secrets(record, forbidden=ctx.forbidden)
            _append(ctx.out_dir / "decisions.jsonl", record)
            decisions[(provider, task.task_id)] = {"record": record, "recommendation": rec}
    return decisions


def _generate(generations: dict, runner, tag: str, prompt: str, task: Task) -> dict:
    """One generation, shared by identical (runner, prompt, request); every user is charged its cost."""
    from time import perf_counter

    key = _sha(f"{tag}\x00{prompt}\x00{task.instructions}")
    if key in generations:
        return {**generations[key], "key": key, "hit": True}
    started = perf_counter()
    try:
        result = runner.run(prompt, task)
        cached = {"output": result.raw_output, "tokens_in": result.tokens_in, "tokens_out": result.tokens_out,
                  "ms": (perf_counter() - started) * 1000, "error": None, "meta": dict(getattr(result, "meta", {}) or {})}
    except (GeneratorBudgetExceeded, BudgetExceeded):
        raise
    except Exception as exc:  # a failed generation is a recorded failure
        cached = {"output": None, "tokens_in": 0, "tokens_out": 0, "ms": (perf_counter() - started) * 1000,
                  "error": f"{type(exc).__name__}: {exc}"[:300], "meta": {}}
    generations[key] = cached
    return {**cached, "key": key, "hit": False}


def _reason_first(ctx, task: UsefulnessTask, record: dict, timings: dict, executor, planner, generations) -> str | None:
    """Reasoning -> prompt -> Rosetta -> execution. The planner (reasoning on) writes a plan; rosetta-core
    turns it into a canonical, validated packet; the executor (reasoning off) follows it. A refusing
    verdict is answered with the contract marker and nothing is executed."""
    request = Task(name=task.task_id, instructions=task.request_text)
    planned = _generate(generations, planner, "planner", PLANNER_PROMPT, request)
    timings["planning"] = planned["ms"]
    record.update(planner_tokens_in=planned["tokens_in"], planner_tokens_out=planned["tokens_out"],
                  planner_reasoning_tokens_est=planned["meta"].get("estimated_reasoning_tokens"),
                  plan_cache_hit=planned["hit"])
    record["generator_tokens_in"], record["generator_tokens_out"] = planned["tokens_in"], planned["tokens_out"]
    if planned["error"]:
        record["error"] = f"planning: {planned['error']}"
        record["plan"] = {"verdict": None, "digest": None, "error": planned["error"]}
        return None
    try:
        plan = parse_plan(planned["output"])
        record["plan"] = {"verdict": plan.verdict, "digest": plan.digest, "error": None,
                          "handoff": plan.verdict in HANDOFF_VERDICTS}
    except PlanError as exc:
        plan = None
        record["plan"] = {"verdict": None, "digest": None, "error": str(exc)[:200]}
    if plan is not None and plan.verdict not in ("PROCEED", *HANDOFF_VERDICTS):
        record["generated"] = True
        record["executor_tokens_in"] = record["executor_tokens_out"] = 0
        return non_proceed_output(plan)

    contract = route_contract(ctx.corpus_dir, record["route"], "M")
    if plan is not None and plan.verdict == "PROCEED":
        prompt, follow = execution_prompt(contract, plan, task.request_text), Task(name=task.task_id, instructions="Follow the plan above.")
    else:  # hand-off verdict or unusable plan: execute the route contract alone, as the M arm does
        prompt, follow = contract, request
    executed = _generate(generations, executor, "executor", prompt, follow)
    timings["generation"] = executed["ms"]
    record["prompt_digest"] = executed["key"]
    record["generation_cache_hit"] = executed["hit"]
    record.update(executor_tokens_in=executed["tokens_in"], executor_tokens_out=executed["tokens_out"])
    record["generator_tokens_in"] += executed["tokens_in"]
    record["generator_tokens_out"] += executed["tokens_out"]
    record["reasoning_tokens_est"] = (planned["meta"].get("estimated_reasoning_tokens") or 0) + (executed["meta"].get("estimated_reasoning_tokens") or 0)
    record["generated"] = executed["error"] is None
    record["error"] = executed["error"]
    return executed["output"]


class FakePlanner:
    """SYNTHETIC offline planner: answers from each task's own definition. Not a model."""

    name = "FAKE"
    model = "fake-planner-1"

    def __init__(self, corpus_dir: Path, garbage=()):
        self.tasks = {t.task_id: t for t in load_tasks(corpus_dir)}
        self.garbage = set(garbage)

    def run(self, prompt_text: str, task: Task | None) -> RunResult:
        item = self.tasks[task.name]
        if item.task_id in self.garbage:
            text = "I think we should just write it."
        else:
            terms = [group[0] if isinstance(group, list) else group
                     for group in item.check.get("conflict_terms", []) + item.check.get("mentions", [])]
            reason = ("conflicting requirements: " + ", ".join(terms)) if terms else "see request"
            verdict = {"unsolvable": "UNSOLVABLE", "false_premise": "PREMISE_REJECTED", "defect": "REPORT_DEFECT",
                       "clarify": "NEEDS_CLARIFICATION"}.get(item.kind, "PROCEED" if item.kind == "code" else "NOT_A_CODE_TASK")
            text = (f"SCHEMA_VER={PLAN_SCHEMA_VER}\nVERDICT={verdict}\nENTRY_POINT={item.entry_point or 'none'}\nSIGNATURE=none\n"
                    f"STEPS=1 read the request | 2 implement it\nEDGE_CASES=none\nREASON={'none' if verdict == 'PROCEED' else reason}\n")
        return RunResult(raw_output=text, tokens_in=len(prompt_text.split()), tokens_out=len(text.split()), latency_ms=0.0,
                         meta={"estimated_reasoning_tokens": 50})


def _arm_trial(ctx, arm: Arm, task: UsefulnessTask, decisions, provider_deciders, generator, sandbox,
               generations, sandboxes, postflights, postflight_reps, planner=None) -> dict:
    timings: dict[str, float] = {}
    record = {
        "arm": arm.arm_id, "rep": arm.rep, "decider": arm.decider, "task_id": task.task_id, "kind": task.kind,
        "language": task.language, "tags": list(task.tags), "decision": None, "route": ctx.baseline_route, "declined_by": None,
        "generated": False, "generation_cache_hit": False, "prompt_digest": None,
        "generator_tokens_in": 0, "generator_tokens_out": 0, "decision_tokens": 0, "decision_calls": 0,
        "code_extracted": False, "sandbox": None, "success": False, "verdict": None, "postflight": None, "error": None,
        "output_digest": None, "raw_output": None,
    }
    if arm.decider != NO_DECIDER:
        used = provider_deciders if arm.decider == CONSENSUS else [arm.decider]
        entries = [decisions[(p, task.task_id)] for p in used]
        rec = consensus([e["recommendation"] for e in entries]) if arm.decider == CONSENSUS else entries[0]["recommendation"]
        record["decision"] = {"outcome": rec.outcome.value, "route": rec.route, "reason_codes": list(rec.reason_codes),
                              "providers": {e["record"]["provider"]: e["record"]["outcome"] for e in entries}}
        record["decision_tokens"] = sum(e["record"]["input_tokens"] for e in entries)
        record["decision_calls"] = sum(e["record"]["calls"] for e in entries)
        timings["decision"] = sum(e["record"]["decision_ms"] for e in entries)  # providers asked one after another
        if rec.outcome in (Outcome.NO_FIT, Outcome.DENY):
            record["route"], record["declined_by"] = None, "decision"
        elif rec.outcome is Outcome.ACCEPT:
            record["route"] = rec.route

    output = None
    if record["route"] is not None:
        if arm.rep == REASON_FIRST:
            output = _reason_first(ctx, task, record, timings, generator, planner, generations)
        else:
            prompt = route_contract(ctx.corpus_dir, record["route"], arm.rep)
            cached = _generate(generations, generator, "generator", prompt, Task(name=task.task_id, instructions=task.request_text))
            record["prompt_digest"] = cached["key"]
            record["generation_cache_hit"] = cached["hit"]
            timings["generation"] = cached["ms"]
            record["generated"] = cached["error"] is None
            record["error"] = cached["error"]
            record["generator_tokens_in"], record["generator_tokens_out"] = cached["tokens_in"], cached["tokens_out"]
            record["reasoning_tokens_est"] = cached["meta"].get("estimated_reasoning_tokens")
            output = cached["output"]
        if output is not None:
            record["raw_output"], record["output_digest"] = output, _sha(output)

    code = extract_code(output)
    record["code_extracted"] = code is not None
    verdict = verify(task, output, VerifyContext(ctx.corpus_dir, sandbox, sandboxes), error=record["error"])
    if verdict.sandbox is not None:
        timings["sandbox"] = verdict.sandbox["ms"]
        record["sandbox"] = {k: v for k, v in verdict.sandbox.items() if k != "ms"}
    record["success"] = verdict.success
    record["verdict"] = {"outcome": verdict.outcome, **verdict.details}
    if task.kind != "code" and output is not None and says_not_applicable(output):
        record["declined_by"] = "generator"

    if code is not None and arm.rep in postflight_reps and arm.decider in ctx.providers:
        pf_key = (arm.decider, _sha(f"{task.task_id}\x00{code}"))
        if pf_key not in postflights:
            _, ask = ctx.ask(arm.decider, ctx.postflight, task, code[:8000], "postflight")
            valid = isinstance(ask.result, AnswerBatch) and not validate_batch(ask.result, ctx.postflight)
            postflights[pf_key] = {"addresses_task": ask.result.answers["addresses_task"].p_yes if valid else None,
                                   "error": None if valid else "invalid or failed postflight answer",
                                   "tokens": ask.input_tokens or 0, "calls": ask.calls, "ms": ask.elapsed_ms}
        pf = postflights[pf_key]
        record["postflight"] = {"addresses_task": pf["addresses_task"], "error": pf["error"]}
        record["decision_tokens"] += pf["tokens"]
        record["decision_calls"] += pf["calls"]
        timings["postflight"] = pf["ms"]

    timings["total"] = sum(timings.values())
    record["timings_ms"] = timings
    record["generator_cost"] = estimate_cost_v2(generator.name, generator.model, record["generator_tokens_in"],
                                                record["generator_tokens_out"]).to_dict()
    if arm.decider == NO_DECIDER:
        record["decision_cost"] = None
    else:
        used = provider_deciders if arm.decider == CONSENSUS else [arm.decider]
        record["decision_cost"] = {
            p: estimate_cost_v2(ctx.providers[p][0].pricing_tool, ctx.providers[p][0].default_model,
                                decisions[(p, task.task_id)]["record"]["input_tokens"], 0).to_dict()
            for p in used
        }
    return record


def _receipt(ctx, record, run_id, repos, arm: Arm, generator, decisions, provider_deciders) -> dict:
    used = provider_deciders if arm.decider == CONSENSUS else [arm.decider]
    entries = [decisions[(p, record["task_id"])]["record"] for p in used]
    served = ",".join(str(e["served_model"]) for e in entries)
    costs = list(record["decision_cost"].values())
    cost = costs[0] if len(costs) == 1 else {"usd": None, "basis": "unknown", "price_source": "mixed providers", "price_as_of": None}
    revision_known = all(
        e["served_model"] and e["served_model"] == ctx.providers[e["provider"]][0].expected_served_model
        and any(ch.isdigit() for ch in e["served_model"]) for e in entries
    )
    decision = record["decision"]
    return {
        "receipt_version": RECEIPT_VERSION, "receipt_id": new_receipt_id(), "run_id": run_id,
        "trial_id": f"{run_id}:{arm.arm_id}:{record['task_id']}", "case_id": record["task_id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "repos": {name: (state or {}).get("sha") for name, state in repos.items()},
        "contract_version": CONTRACT_VERSION,
        "state": {"schema_version": STATE_SCHEMA_VERSION, "digest": entries[0]["state_digest"],
                  "snapshot_ref": f"exchanges.jsonl#{record['task_id']}"},
        "replay": "available",
        "question_set": {"set_id": ctx.intake.set_id, "version": ctx.intake.version, "hash": ctx.intake.content_hash()},
        "policy": {"policy_id": "intake-placeholder" if arm.decider != CONSENSUS else "intake-placeholder+consensus",
                   "version": "0.1", "calibrated": False},
        "provider": {"name": arm.decider if arm.decider != CONSENSUS else "consensus:" + "+".join(used),
                     "requested_model": ",".join(ctx.providers[p][0].default_model for p in used),
                     "served_model": served, "revision_known": bool(revision_known)},
        "answers_ref": f"decisions.jsonl#{record['task_id']}",
        "recommendation": {"outcome": decision["outcome"], "route": decision["route"], "reason_codes": decision["reason_codes"]},
        "executed_route": record["route"],
        "mode": "enforced",
        "generator": {"tool": generator.name, "model": generator.model, "settings": {"representation": arm.rep}},
        "usage": {"decision_input_tokens": record["decision_tokens"], "generator_tokens_in": record["generator_tokens_in"],
                  "generator_tokens_out": record["generator_tokens_out"]},
        "cost": cost,
        "timings_ms": record["timings_ms"],
        "retries": {"transport": sum(e.get("transport_retries", 0) for e in entries), "semantic": 0},
        "output_digest": record["output_digest"],
        "outcome": {"verified_success": record["success"],
                    "checks": {"acceptance_tests": record["sandbox"]["passed"] if record["sandbox"] else None,
                               "no_code_produced": (not record["code_extracted"]) if record["kind"] == "no_code" else None}},
        "override": None,
    }
