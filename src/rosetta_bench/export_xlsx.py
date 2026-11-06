from collections import defaultdict
from pathlib import Path

import openpyxl

from rosetta_bench.storage import load_trials

_SUMMARY_HEADER = (
    "tool", "prompt_format", "mean_latency_ms", "mean_tokens_in",
    "mean_tokens_out", "mean_quality_score", "mean_cost_usd", "n",
)


def export_to_xlsx(csv_path: Path, xlsx_path: Path) -> None:
    rows = load_trials(csv_path)

    workbook = openpyxl.Workbook()
    raw_sheet = workbook.active
    raw_sheet.title = "raw_data"
    if rows:
        raw_sheet.append(list(rows[0].keys()))
        for row in rows:
            raw_sheet.append(list(row.values()))

    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        groups[(row["tool"], row["prompt_format"])].append(row)

    summary_sheet = workbook.create_sheet("summary")
    summary_sheet.append(list(_SUMMARY_HEADER))
    for (tool, prompt_format), group_rows in sorted(groups.items()):
        n = len(group_rows)
        latencies = [float(r["latency_ms"]) for r in group_rows]
        tokens_in = [float(r["tokens_in"]) for r in group_rows]
        tokens_out = [float(r["tokens_out"]) for r in group_rows]
        quality_scores = [float(r["quality_score"]) for r in group_rows if r["quality_score"]]
        costs = [float(r["cost_usd"]) for r in group_rows]
        summary_sheet.append([
            tool,
            prompt_format,
            sum(latencies) / n,
            sum(tokens_in) / n,
            sum(tokens_out) / n,
            (sum(quality_scores) / len(quality_scores)) if quality_scores else None,
            sum(costs) / n,
            n,
        ])

    workbook.save(xlsx_path)
