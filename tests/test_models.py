from rosetta_bench.models import Task, RunResult, Trial

CANONICAL_COLUMNS = [
    "trial_id", "timestamp", "tool", "model", "prompt_id", "prompt_format",
    "suite", "tokens_in", "tokens_out", "latency_ms", "turns", "task_success",
    "comprehension_accuracy", "quality_score", "judge_justification",
    "cost_usd", "raw_output",
]


def test_task_holds_instructions_and_optional_reference():
    task = Task(name="validate", instructions="do the thing")
    assert task.reference_output is None
    task2 = Task(name="validate", instructions="do the thing", reference_output="expected")
    assert task2.reference_output == "expected"


def test_run_result_defaults_turns_to_one():
    result = RunResult(raw_output="hi", tokens_in=10, tokens_out=5, latency_ms=123.4)
    assert result.turns == 1


def test_trial_to_row_has_canonical_columns_in_order():
    trial = Trial(
        trial_id="t1", timestamp="2026-07-13T00:00:00Z", tool="CLAUDE", model="claude-sonnet-5",
        prompt_id="rosetta_build", prompt_format="MACHINE", suite="COMPREHENSION",
        tokens_in=100, tokens_out=20, latency_ms=456.0, turns=1, task_success=None,
        comprehension_accuracy=0.9, quality_score=None, judge_justification="",
        cost_usd=0.001, raw_output="the answer",
    )
    row = trial.to_row()
    assert list(row.keys()) == CANONICAL_COLUMNS
    assert row["tool"] == "CLAUDE"
    assert row["comprehension_accuracy"] == 0.9
