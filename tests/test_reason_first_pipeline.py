"""Reason-first (R) arm in the usefulness matrix, offline with synthetic fakes."""
import json
from pathlib import Path

import pytest

pytest.importorskip("rosetta_core.decision", reason="needs rosetta-core")

from test_usefulness_v2 import CORPUS, TASKS, FakeSandbox

from rosetta_bench.cli import main
from rosetta_bench.decision.fake_provider import FakeSystemOne
from rosetta_bench.decision.profiles import PROFILES
from rosetta_bench.decision.transport import FakeTransport, TransportUnavailable
from rosetta_bench.usefulness import pipeline
from rosetta_bench.usefulness.pipeline import BudgetedGenerator, FakeCodeGenerator, FakePlanner, run_matrix

BY_ID = {t.task_id: t for t in TASKS}


def _lines(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _run(tmp_path, name="r", planner=None, reps=("M", "R"), deciders=("none",), providers=None):
    generator = FakeCodeGenerator(CORPUS, broken=(), codes_anyway=())
    planner = planner or FakePlanner(CORPUS)
    return run_matrix(CORPUS, list(reps), list(deciders), BudgetedGenerator(generator, None),
                      {"kind": "fake", "model": generator.model, "settings": {}}, tmp_path / name, seed=2, live=False,
                      sandbox=FakeSandbox(), planner=BudgetedGenerator(planner, None),
                      planner_meta={"kind": "fake", "model": planner.model}, providers=providers)


def test_refusing_plan_verdicts_are_answered_without_execution(tmp_path):
    trials = [t for t in _lines(_run(tmp_path) / "trials.jsonl") if t["rep"] == "R"]
    refusing = [t for t in trials if BY_ID[t["task_id"]].kind in ("unsolvable", "false_premise")]
    assert refusing
    for t in refusing:
        assert t["plan"]["verdict"] in ("UNSOLVABLE", "PREMISE_REJECTED")
        assert t["executor_tokens_in"] == 0 and "generation" not in t["timings_ms"] and "planning" in t["timings_ms"]
        assert t["success"], (t["task_id"], t["verdict"])


HANDOFF_KINDS = ("no_code", "data_query", "docs_edit", "translation_review", "clarify")


def test_hand_off_verdicts_execute_the_route_contract_without_a_plan(tmp_path):
    """Run 20 (live) lost every non-code task: NOT_A_CODE_TASK was answered with the bare marker.
    Not a code task, or missing details, is the route contract's job, so the executor answers it."""
    trials = _lines(_run(tmp_path) / "trials.jsonl")
    m_prompts = {t["task_id"]: t for t in trials if t["rep"] == "M"}
    handed = [t for t in trials if t["rep"] == "R" and BY_ID[t["task_id"]].kind in HANDOFF_KINDS]
    assert {BY_ID[t["task_id"]].kind for t in handed} == set(HANDOFF_KINDS)
    for t in handed:
        assert t["plan"]["verdict"] in ("NOT_A_CODE_TASK", "NEEDS_CLARIFICATION") and t["plan"]["handoff"] is True
        assert t["executor_tokens_in"] > 0 and {"planning", "generation"} <= set(t["timings_ms"])
        assert t["executor_tokens_in"] == m_prompts[t["task_id"]]["generator_tokens_in"]  # same prompt as the M arm
        assert t["success"] == m_prompts[t["task_id"]]["success"], t["task_id"]


def test_proceeding_plans_are_executed_with_the_plan_packet_and_both_costs_are_charged(tmp_path):
    trials = [t for t in _lines(_run(tmp_path) / "trials.jsonl") if t["rep"] == "R" and t["plan"]["verdict"] == "PROCEED"]
    assert trials
    for t in trials:
        assert len(t["plan"]["digest"]) == 64
        assert t["generator_tokens_in"] == t["planner_tokens_in"] + t["executor_tokens_in"]
        assert {"planning", "generation"} <= set(t["timings_ms"])
        assert t["reasoning_tokens_est"] == 50  # synthetic planner reports 50, the fake executor none


def test_an_unusable_plan_falls_back_to_executing_without_one(tmp_path):
    code_task = next(t.task_id for t in TASKS if t.kind == "code")
    trials = _lines(_run(tmp_path, planner=FakePlanner(CORPUS, garbage=(code_task,))) / "trials.jsonl")
    fallback = next(t for t in trials if t["rep"] == "R" and t["task_id"] == code_task)
    assert fallback["plan"]["error"] and fallback["plan"]["verdict"] is None
    assert fallback["generated"] and fallback["executor_tokens_in"] > 0


def test_reason_first_needs_a_planner(tmp_path):
    generator = FakeCodeGenerator(CORPUS)
    with pytest.raises(ValueError):
        run_matrix(CORPUS, ["R"], ["none"], BudgetedGenerator(generator, None), {"kind": "fake", "model": "x", "settings": {}},
                   tmp_path / "x", seed=1, live=False, sandbox=FakeSandbox())


def test_cli_runs_the_reason_first_arm(tmp_path):
    pipeline.SANDBOX_FACTORY = lambda: FakeSandbox()
    try:
        assert main(["usefulness", "run", "--corpus", str(CORPUS), "--reps", "M,R", "--deciders", "none",
                     "--generator", "fake", "--out", str(tmp_path / "cli")]) == 0
    finally:
        pipeline.SANDBOX_FACTORY = None
    manifest = json.loads((tmp_path / "cli" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["planner"]["model"] == "fake-planner-1" and "R" in manifest["representations"]


class FlakyOnce:
    """Fails the very first call with a connection error, then delegates."""

    def __init__(self, inner):
        self.inner, self.failed = inner, False

    def post(self, url, headers, body, timeout_s):
        if not self.failed:
            self.failed = True
            raise TransportUnavailable("simulated reset")
        return self.inner.post(url, headers, body, timeout_s)


def test_receipts_record_real_transport_retries(tmp_path):
    providers = {"fake": (PROFILES["fake"], FlakyOnce(FakeTransport(FakeSystemOne())), None)}
    out = _run(tmp_path, reps=("M",), deciders=("fake",), providers=providers)
    receipts = _lines(out / "receipts.jsonl")
    assert sum(r["retries"]["transport"] for r in receipts) == 1
