from pathlib import Path
from rosetta_bench.models import Trial
from rosetta_bench.storage import append_trial, load_trials


def _make_trial(trial_id: str) -> Trial:
    return Trial(
        trial_id=trial_id, timestamp="2026-07-13T00:00:00Z", tool="CLAUDE", model="claude-sonnet-5",
        prompt_id="rosetta_build", prompt_format="MACHINE", suite="COMPREHENSION",
        tokens_in=100, tokens_out=20, latency_ms=456.0, turns=1, task_success=None,
        comprehension_accuracy=0.9, quality_score=None, judge_justification="",
        cost_usd=0.001, raw_output="the answer",
    )


def test_append_trial_creates_file_with_header(tmp_path: Path):
    path = tmp_path / "trials.csv"
    append_trial(_make_trial("t1"), path)

    rows = load_trials(path)
    assert len(rows) == 1
    assert rows[0]["trial_id"] == "t1"
    assert rows[0]["tool"] == "CLAUDE"


def test_append_trial_appends_without_duplicating_header(tmp_path: Path):
    path = tmp_path / "trials.csv"
    append_trial(_make_trial("t1"), path)
    append_trial(_make_trial("t2"), path)

    rows = load_trials(path)
    assert len(rows) == 2
    assert [r["trial_id"] for r in rows] == ["t1", "t2"]
    header_line = path.read_text(encoding="utf-8").splitlines()[0]
    assert header_line.count("trial_id") == 1
