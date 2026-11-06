from pathlib import Path
import openpyxl
from rosetta_bench.export_xlsx import export_to_xlsx
from rosetta_bench.models import Trial
from rosetta_bench.storage import append_trial


def _make_trial(trial_id: str, tool: str, prompt_format: str, latency_ms: float) -> Trial:
    return Trial(
        trial_id=trial_id, timestamp="2026-07-13T00:00:00Z", tool=tool, model="m1",
        prompt_id="rosetta_build", prompt_format=prompt_format, suite="TASK_COMPLETION",
        tokens_in=100, tokens_out=20, latency_ms=latency_ms, turns=1, task_success=None,
        comprehension_accuracy=None, quality_score=4.0, judge_justification="ok",
        cost_usd=0.01, raw_output="output",
    )


def test_export_creates_raw_data_and_summary_sheets(tmp_path: Path):
    csv_path = tmp_path / "trials.csv"
    append_trial(_make_trial("t1", "CLAUDE", "MACHINE", 100.0), csv_path)
    append_trial(_make_trial("t2", "CLAUDE", "MACHINE", 200.0), csv_path)
    append_trial(_make_trial("t3", "CLAUDE", "HUMAN", 500.0), csv_path)
    xlsx_path = tmp_path / "trials.xlsx"

    export_to_xlsx(csv_path, xlsx_path)

    workbook = openpyxl.load_workbook(xlsx_path)
    assert set(workbook.sheetnames) == {"raw_data", "summary"}

    raw_sheet = workbook["raw_data"]
    assert raw_sheet["A1"].value == "trial_id"
    assert raw_sheet.max_row == 4  # header + 3 rows

    summary_sheet = workbook["summary"]
    summary_rows = list(summary_sheet.iter_rows(values_only=True))
    assert summary_rows[0] == ("tool", "prompt_format", "mean_latency_ms", "mean_tokens_in", "mean_tokens_out", "mean_quality_score", "mean_cost_usd", "n")
    machine_row = next(r for r in summary_rows[1:] if r[0] == "CLAUDE" and r[1] == "MACHINE")
    assert machine_row[2] == 150.0  # mean of 100.0 and 200.0
    assert machine_row[7] == 2  # n
