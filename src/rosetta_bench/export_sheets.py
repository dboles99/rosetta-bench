"""Google Sheets export. `GSpreadClient` makes live Google API calls -- not
covered by the automated test suite (requires GOOGLE_SERVICE_ACCOUNT_JSON).
`export_to_sheets` itself is fully tested via a fake client.
"""
from collections import defaultdict
from pathlib import Path
from typing import Protocol

from rosetta_bench.storage import load_trials

_SUMMARY_HEADER = [
    "tool", "prompt_format", "mean_latency_ms", "mean_tokens_in",
    "mean_tokens_out", "mean_quality_score", "mean_cost_usd", "n",
]


class SpreadsheetProtocol(Protocol):
    def update_sheet(self, worksheet_name: str, rows: list[list]) -> None:
        ...


class GSpreadClientProtocol(Protocol):
    def open_or_create(self, sheet_name: str) -> SpreadsheetProtocol:
        ...


def export_to_sheets(csv_path: Path, sheet_name: str, client: GSpreadClientProtocol) -> None:
    rows = load_trials(csv_path)
    spreadsheet = client.open_or_create(sheet_name)

    raw_rows: list[list] = []
    if rows:
        raw_rows.append(list(rows[0].keys()))
        for row in rows:
            raw_rows.append(list(row.values()))
    spreadsheet.update_sheet("raw_data", raw_rows)

    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        groups[(row["tool"], row["prompt_format"])].append(row)

    summary_rows: list[list] = [list(_SUMMARY_HEADER)]
    for (tool, prompt_format), group_rows in sorted(groups.items()):
        n = len(group_rows)
        latencies = [float(r["latency_ms"]) for r in group_rows]
        tokens_in = [float(r["tokens_in"]) for r in group_rows]
        tokens_out = [float(r["tokens_out"]) for r in group_rows]
        quality_scores = [float(r["quality_score"]) for r in group_rows if r["quality_score"]]
        costs = [float(r["cost_usd"]) for r in group_rows]
        summary_rows.append([
            tool,
            prompt_format,
            sum(latencies) / n,
            sum(tokens_in) / n,
            sum(tokens_out) / n,
            (sum(quality_scores) / len(quality_scores)) if quality_scores else None,
            sum(costs) / n,
            n,
        ])
    spreadsheet.update_sheet("summary", summary_rows)


class GSpreadClient:
    """Live adapter around the `gspread` package. Not covered by tests."""

    def __init__(self, service_account_json_path: str):
        import gspread

        self._client = gspread.service_account(filename=service_account_json_path)

    def open_or_create(self, sheet_name: str):
        try:
            spreadsheet = self._client.open(sheet_name)
        except Exception:
            spreadsheet = self._client.create(sheet_name)
        return _GSpreadSpreadsheetAdapter(spreadsheet)


class _GSpreadSpreadsheetAdapter:
    def __init__(self, spreadsheet):
        self._spreadsheet = spreadsheet

    def update_sheet(self, worksheet_name: str, rows: list[list]) -> None:
        try:
            worksheet = self._spreadsheet.worksheet(worksheet_name)
        except Exception:
            worksheet = self._spreadsheet.add_worksheet(title=worksheet_name, rows=1, cols=1)
        worksheet.clear()
        if rows:
            worksheet.update(rows)
