from pathlib import Path
from rosetta_bench.export_sheets import export_to_sheets
from rosetta_bench.models import Trial
from rosetta_bench.storage import append_trial


class FakeSpreadsheet:
    def __init__(self):
        self.worksheets: dict[str, list[list]] = {}

    def update_sheet(self, worksheet_name: str, rows: list[list]) -> None:
        self.worksheets[worksheet_name] = rows


class FakeGSpreadClient:
    def __init__(self):
        self.spreadsheet = FakeSpreadsheet()
        self.opened_names: list[str] = []

    def open_or_create(self, sheet_name: str):
        self.opened_names.append(sheet_name)
        return self.spreadsheet


def _make_trial(trial_id: str, tool: str, prompt_format: str) -> Trial:
    return Trial(
        trial_id=trial_id, timestamp="2026-07-13T00:00:00Z", tool=tool, model="m1",
        prompt_id="rosetta_build", prompt_format=prompt_format, suite="TASK_COMPLETION",
        tokens_in=100, tokens_out=20, latency_ms=150.0, turns=1, task_success=None,
        comprehension_accuracy=None, quality_score=4.0, judge_justification="ok",
        cost_usd=0.01, raw_output="output",
    )


def test_export_opens_named_sheet_and_writes_both_worksheets(tmp_path: Path):
    csv_path = tmp_path / "trials.csv"
    append_trial(_make_trial("t1", "CLAUDE", "MACHINE"), csv_path)
    client = FakeGSpreadClient()

    export_to_sheets(csv_path, "rosetta-bench results", client)

    assert client.opened_names == ["rosetta-bench results"]
    assert "raw_data" in client.spreadsheet.worksheets
    assert "summary" in client.spreadsheet.worksheets
    raw_rows = client.spreadsheet.worksheets["raw_data"]
    assert raw_rows[0][0] == "trial_id"
    assert raw_rows[1][0] == "t1"
