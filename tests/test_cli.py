from pathlib import Path
from rosetta_bench.cli import main
from rosetta_bench.models import Trial
from rosetta_bench.storage import append_trial


def _make_trial(trial_id: str) -> Trial:
    return Trial(
        trial_id=trial_id, timestamp="2026-07-13T00:00:00Z", tool="CLAUDE", model="m1",
        prompt_id="rosetta_build", prompt_format="MACHINE", suite="TASK_COMPLETION",
        tokens_in=10, tokens_out=5, latency_ms=100.0, turns=1, task_success=None,
        comprehension_accuracy=None, quality_score=4.0, judge_justification="ok",
        cost_usd=0.01, raw_output="output",
    )


def test_export_xlsx_command_writes_file(tmp_path: Path):
    csv_path = tmp_path / "trials.csv"
    append_trial(_make_trial("t1"), csv_path)
    xlsx_path = tmp_path / "out.xlsx"

    code = main(["export", "xlsx", "--csv", str(csv_path), "--out", str(xlsx_path)])

    assert code == 0
    assert xlsx_path.exists()


def test_run_command_returns_nonzero_and_explains_manual_invocation(capsys):
    code = main(["run"])

    assert code == 1
    captured = capsys.readouterr()
    assert "not automated" in captured.err.lower() or "credentials" in captured.err.lower()
