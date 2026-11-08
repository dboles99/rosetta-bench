import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

pytest.importorskip("rosetta_core.decision", reason="usefulness tests need rosetta-core installed")

from rosetta_core.decision import Outcome, Recommendation

from rosetta_bench.cli import main
from rosetta_bench.sandbox import SandboxResult
from rosetta_bench.usefulness.corpus import hidden_tests, load_tasks, route_contract
from rosetta_bench.usefulness.extract import extract_code, says_not_applicable
from rosetta_bench.usefulness.pipeline import consensus

CORPUS = Path(__file__).resolve().parent.parent / "corpus" / "usefulness_v1"
REPS, DECIDERS = ["P", "H", "M"], ["none", "fake", "fake-b", "consensus"]


def _lines(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()] if path.exists() else []


# --- corpus quality -------------------------------------------------------------------

def test_every_code_task_has_hidden_tests_and_a_reference():
    tasks = load_tasks(CORPUS)
    code = [t for t in tasks if t.kind == "code"]
    assert len(code) >= 12 and any(t.kind == "no_code" for t in tasks)
    for task in code:
        assert f"from solution import {task.entry_point}" in hidden_tests(CORPUS, task)
        assert (CORPUS / "reference" / f"{task.task_id}.py").exists()


def test_references_pass_and_a_stub_fails_every_hidden_test_file():
    """Trusted check: the reference solutions were written with the tasks, so they run locally."""
    for task in (t for t in load_tasks(CORPUS) if t.kind == "code"):
        for solution, should_pass in (((CORPUS / "reference" / f"{task.task_id}.py").read_text(encoding="utf-8"), True),
                                      (f"def {task.entry_point}(*args, **kwargs):\n    return None\n", False)):
            with tempfile.TemporaryDirectory() as tmp:
                Path(tmp, "solution.py").write_text(solution, encoding="utf-8")
                Path(tmp, "test_task.py").write_text(hidden_tests(CORPUS, task), encoding="utf-8")
                proc = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", tmp, "-p", "test_*.py"],
                                      capture_output=True, text=True, cwd=tmp, timeout=60)
            assert (proc.returncode == 0) is should_pass, f"{task.task_id} pass={should_pass}: {proc.stderr[-400:]}"


def test_three_representations_of_the_same_contract():
    plain = route_contract(CORPUS, "code_change", "P")
    human = route_contract(CORPUS, "code_change", "H")
    machine = route_contract(CORPUS, "code_change", "M")
    assert "NOT_A_CODE_TASK" in plain and "ROSETTA" not in plain and "ROUTE=" not in plain
    assert "<!-- ROSETTA:NOTES" in human and "- ROUTE: code_change" in human
    assert machine.startswith("SCHEMA_VER=1.0\n") and "ROUTE=code_change" in machine and "NOTES" not in machine
    assert all("unittest" not in text for text in (plain, human, machine))


# --- extraction ------------------------------------------------------------------------

def test_extract_takes_the_last_python_block():
    text = "intro\n```python\nx = 1\n```\nmore\n```python\ndef f():\n    return 2\n```\n"
    assert extract_code(text) == "def f():\n    return 2\n"


def test_extract_accepts_an_unlabelled_block_and_returns_none_without_one():
    assert extract_code("```\ny = 3\n```") == "y = 3\n"
    assert extract_code("no code here") is None


def test_not_applicable_reply_is_recognised():
    assert says_not_applicable("NOT_A_CODE_TASK")
    assert says_not_applicable("  NOT_A_DOCS_TASK\n")
    assert not says_not_applicable("def f(): pass")


# --- consensus -------------------------------------------------------------------------

def _rec(outcome, route=None):
    return Recommendation(outcome, route, ())


def test_consensus_accepts_only_when_every_provider_picks_the_same_route():
    assert consensus([_rec(Outcome.ACCEPT, "docs_edit"), _rec(Outcome.ACCEPT, "docs_edit")]).route == "docs_edit"
    split = consensus([_rec(Outcome.ACCEPT, "docs_edit"), _rec(Outcome.ACCEPT, "code_change")])
    assert split.outcome is Outcome.ABSTAIN and split.reason_codes == ("NO_CONSENSUS",)


def test_consensus_declines_only_when_every_provider_says_no_fit_and_any_deny_wins():
    assert consensus([_rec(Outcome.NO_FIT), _rec(Outcome.NO_FIT)]).outcome is Outcome.NO_FIT
    assert consensus([_rec(Outcome.NO_FIT), _rec(Outcome.ACCEPT, "clarify")]).outcome is Outcome.ABSTAIN
    assert consensus([_rec(Outcome.ACCEPT, "code_change"), _rec(Outcome.DENY)]).outcome is Outcome.DENY


# --- matrix run (offline, synthetic) ---------------------------------------------------

class FakeSandbox:
    """Passes code that defines a function and is not marked broken. No execution."""

    def __init__(self):
        self.calls = 0

    def run_tests(self, files):
        self.calls += 1
        code = files["solution.py"]
        passed = "BROKEN" not in code and "def " in code
        return SandboxResult(passed, 3, 0 if passed else 1, False, 0, "", "", 1.0)


def _run(tmp_path: Path, *extra, sandbox=None, name="matrix"):
    from rosetta_bench.usefulness import pipeline

    out = tmp_path / name
    pipeline.SANDBOX_FACTORY = (lambda: sandbox) if sandbox is not None else (lambda: FakeSandbox())
    try:
        code = main(["usefulness", "run", "--corpus", str(CORPUS), "--reps", ",".join(REPS), "--deciders", ",".join(DECIDERS),
                     "--generator", "fake", "--postflight-reps", "M", "--out", str(out), *extra])
    finally:
        pipeline.SANDBOX_FACTORY = None
    return code, out


def test_matrix_run_scores_every_arm_and_task(tmp_path: Path):
    code, out = _run(tmp_path)
    assert code == 0
    trials = _lines(out / "trials.jsonl")
    tasks = load_tasks(CORPUS)
    assert len(trials) == len(REPS) * len(DECIDERS) * len(tasks)
    assert {t["arm"] for t in trials} == {f"{r}+{d}" for r in REPS for d in DECIDERS}
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["synthetic"] is True and manifest["live"] is False
    for trial in trials:
        assert trial["success"] in (True, False)
        assert trial["timings_ms"]["total"] >= 0
        assert trial["generator_cost"]["basis"] == "free_local"


def test_decisions_are_made_once_per_provider_and_task(tmp_path: Path):
    code, out = _run(tmp_path)
    decisions = _lines(out / "decisions.jsonl")
    tasks = load_tasks(CORPUS)
    assert len(decisions) == 2 * len(tasks)
    assert {d["provider"] for d in decisions} == {"fake", "fake-b"}


def test_identical_prompts_share_one_generation_but_every_arm_is_charged(tmp_path: Path):
    code, out = _run(tmp_path)
    trials = _lines(out / "trials.jsonl")
    generated = [t for t in trials if t["generated"]]
    originals = {t["prompt_digest"]: t for t in generated if not t["generation_cache_hit"]}
    assert len(originals) < len(generated)
    for trial in generated:
        source = originals[trial["prompt_digest"]]
        assert trial["generator_tokens_out"] == source["generator_tokens_out"]
        assert trial["timings_ms"]["generation"] == source["timings_ms"]["generation"]


def test_no_fit_declines_skip_generation_and_abstentions_fall_back(tmp_path: Path):
    code, out = _run(tmp_path)
    trials = _lines(out / "trials.jsonl")
    declined = [t for t in trials if t["declined_by"] == "decision"]
    assert declined and all(not t["generated"] and t["generator_tokens_in"] == 0 for t in declined)
    fallen_back = [t for t in trials if t["decision"] and t["decision"]["outcome"] in ("ABSTAIN", "FALLBACK")]
    assert fallen_back and all(t["route"] == "code_change" for t in fallen_back)


def test_postflight_is_advisory_and_only_on_requested_representations(tmp_path: Path):
    code, out = _run(tmp_path)
    checked = [t for t in _lines(out / "trials.jsonl") if t["postflight"] is not None]
    assert checked and all(t["rep"] == "M" and t["decider"] in ("fake", "fake-b") and t["generated"] for t in checked)


def test_receipts_validate_for_every_decision_arm(tmp_path: Path):
    from rosetta_core.decision import validate_receipt

    code, out = _run(tmp_path)
    receipts = _lines(out / "receipts.jsonl")
    assert len(receipts) == len(REPS) * 3 * len(load_tasks(CORPUS))
    for receipt in receipts:
        validate_receipt(receipt)


def test_report_has_the_matrix_and_the_requested_contrasts(tmp_path: Path):
    code, out = _run(tmp_path)
    assert main(["usefulness", "report", "--run", str(out)]) == 0
    report = (out / "usefulness_report.md").read_text(encoding="utf-8")
    for needle in ("SYNTHETIC", "## Matrix", "Tokens per verified success", "## Representation contrasts",
                   "P vs M", "## Decision contrasts", "none vs fake", "Decline precision"):
        assert needle in report, needle


def test_live_generator_needs_the_live_flag_and_budgets(tmp_path: Path, capsys):
    base = ["usefulness", "run", "--corpus", str(CORPUS), "--reps", "M", "--deciders", "none", "--generator", "ollama"]
    assert main(base + ["--out", str(tmp_path / "x")]) == 2 and "--live" in capsys.readouterr().err
    assert main(base + ["--live", "--out", str(tmp_path / "y")]) == 2 and "--max-generator-calls" in capsys.readouterr().err


def test_generator_budget_stops_the_run(tmp_path: Path):
    code, out = _run(tmp_path, "--max-generator-calls", "4")
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["stopped_early"].startswith("generator budget")
    trials = _lines(out / "trials.jsonl")
    assert sum(t["generated"] and not t["generation_cache_hit"] for t in trials) == 4
