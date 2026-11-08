import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

pytest.importorskip("rosetta_core.decision", reason="usefulness tests need rosetta-core installed")

from rosetta_bench.cli import main
from rosetta_bench.sandbox import SandboxResult
from rosetta_bench.usefulness.corpus import hidden_tests, load_tasks, route_contract
from rosetta_bench.usefulness.extract import extract_code, says_not_applicable

CORPUS = Path(__file__).resolve().parent.parent / "corpus" / "usefulness_v1"


def _lines(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


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


def test_route_contracts_load_through_rosetta_core():
    machine = route_contract(CORPUS, "code_change", "MACHINE")
    human = route_contract(CORPUS, "code_change", "HUMAN")
    assert machine.startswith("SCHEMA_VER=1.0\n") and "ROUTE=code_change" in machine
    assert "<!-- ROSETTA:NOTES" in human and "NOT_A_CODE_TASK" in human
    assert "unittest" not in machine and "unittest" not in human


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


# --- pipeline (offline, synthetic) -----------------------------------------------------

class FakeSandbox:
    """Passes code that defines the entry point and is not marked broken. No execution."""

    def __init__(self):
        self.calls = 0

    def run_tests(self, files):
        self.calls += 1
        code = files["solution.py"]
        passed = "BROKEN" not in code and "def " in code
        return SandboxResult(passed, 3, 0 if passed else 1, False, 0, "", "", 1.0)


def _run(tmp_path: Path, *extra, sandbox=None):
    from rosetta_bench.usefulness import pipeline

    out = tmp_path / "useful"
    if sandbox is not None:
        pipeline.SANDBOX_FACTORY = lambda: sandbox
    try:
        code = main(["usefulness", "run", "--corpus", str(CORPUS), "--arms", "A,B,C", "--generator", "fake",
                     "--decision", "fake", "--postflight", "--out", str(out), *extra])
    finally:
        pipeline.SANDBOX_FACTORY = None
    return code, out


def test_offline_run_scores_every_arm_and_task(tmp_path: Path):
    sandbox = FakeSandbox()
    code, out = _run(tmp_path, sandbox=sandbox)
    assert code == 0
    trials = _lines(out / "trials.jsonl")
    tasks = load_tasks(CORPUS)
    assert len(trials) == 3 * len(tasks)
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["synthetic"] is True and manifest["live"] is False
    for trial in trials:
        assert trial["success"] in (True, False)
        assert "total" in trial["timings_ms"]
        assert ("generation" in trial["timings_ms"]) == trial["generated"] or trial["error"]
        assert trial["generator_cost"]["basis"] == "free_local"
    by_arm = {arm: [t for t in trials if t["arm"] == arm] for arm in "ABC"}
    assert all(t["route_decision"] is None for t in by_arm["A"] + by_arm["B"])
    assert all(t["route_decision"] is not None for t in by_arm["C"])


def test_decision_arm_declines_no_fit_without_calling_the_generator(tmp_path: Path):
    code, out = _run(tmp_path, sandbox=FakeSandbox())
    trials = _lines(out / "trials.jsonl")
    declined = [t for t in trials if t["arm"] == "C" and t["route_decision"]["outcome"] in ("NO_FIT", "DENY")]
    assert declined, "the synthetic decider should refuse at least one no-code request"
    assert all(not t["generated"] and t["generator_tokens_in"] == 0 for t in declined)
    abstained = [t for t in trials if t["arm"] == "C" and t["route_decision"]["outcome"] in ("ABSTAIN", "FALLBACK")]
    assert all(t["route"] == "code_change" for t in abstained)


def test_postflight_is_advisory_and_recorded(tmp_path: Path):
    code, out = _run(tmp_path, sandbox=FakeSandbox())
    trials = _lines(out / "trials.jsonl")
    checked = [t for t in trials if t["postflight"] is not None]
    assert checked and all(t["arm"] == "C" and t["generated"] for t in checked)
    assert all(0.0 <= t["postflight"]["addresses_task"] <= 1.0 for t in checked)


def test_receipts_for_the_decision_arm_validate(tmp_path: Path):
    from rosetta_core.decision import validate_receipt

    code, out = _run(tmp_path, sandbox=FakeSandbox())
    receipts = _lines(out / "receipts.jsonl")
    assert receipts and all(r["mode"] == "enforced" for r in receipts)
    for receipt in receipts:
        validate_receipt(receipt)


def test_report_shows_tokens_per_verified_success(tmp_path: Path):
    code, out = _run(tmp_path, sandbox=FakeSandbox())
    assert main(["usefulness", "report", "--run", str(out)]) == 0
    report = (out / "usefulness_report.md").read_text(encoding="utf-8")
    assert "SYNTHETIC" in report and "Tokens per verified success" in report and "| C |" in report


def test_live_generator_needs_the_live_flag_and_budgets(tmp_path: Path, capsys):
    code = main(["usefulness", "run", "--corpus", str(CORPUS), "--arms", "B", "--generator", "ollama",
                 "--generator-model", "kimi-k2.7-code:cloud", "--out", str(tmp_path / "x")])
    assert code == 2 and "--live" in capsys.readouterr().err
    code = main(["usefulness", "run", "--corpus", str(CORPUS), "--arms", "B", "--generator", "ollama",
                 "--generator-model", "kimi-k2.7-code:cloud", "--live", "--out", str(tmp_path / "y")])
    assert code == 2 and "--max-generator-calls" in capsys.readouterr().err


def test_generator_budget_stops_the_run(tmp_path: Path):
    code, out = _run(tmp_path, "--max-generator-calls", "4", sandbox=FakeSandbox())
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["stopped_early"].startswith("generator budget")
    assert sum(t["generated"] for t in _lines(out / "trials.jsonl")) == 4
