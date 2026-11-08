"""Markdown report for one run directory. Costs are summed only where known; the
number of unknown-cost trials is shown, never folded in as zero."""
from collections import defaultdict
from pathlib import Path

from rosetta_bench.results_v2 import load_manifest, load_trials_v2

MIN_CASES_FOR_INTERVALS = 10


def _mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def _percentile(values, fraction):
    values = sorted(v for v in values if v is not None)
    if not values:
        return None
    rank = max(1, -(-int(fraction * 100) * len(values) // 100))  # nearest-rank
    return values[min(rank, len(values)) - 1]


def _fmt(value, digits=3):
    if value is None:
        return "–"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _case_metric(trial):
    if trial["suite"] == "COMPREHENSION":
        return trial["comprehension_accuracy"]
    success = trial["task_success"]
    return None if success is None else float(success)


def build_report(run_dir: Path) -> str:
    manifest = load_manifest(run_dir)
    trials = load_trials_v2(run_dir)
    lines = [f"# Run {manifest['run_id']}: {manifest['experiment']}", ""]
    if manifest["synthetic"]:
        lines += [
            "> **SYNTHETIC: wiring check only.** Every arm used an offline fake generator. These numbers "
            "describe the corpus files and the scorers, not any model, and are not evidence for any claim.",
            "",
        ]
    lines += [
        f"- Cases: {len(manifest['case_ids'])} (the unit of paired resampling)",
        f"- Trials: {len(trials)}; seed {manifest['seed']}; repeats {manifest.get('repeats', 1)} (repeats are not new cases)",
        f"- Bench repo: {manifest['repos'].get('bench')}",
        "",
        "## Per arm and suite",
        "",
        "| Arm | Suite | Format | n | Errors | Comprehension accuracy | Task success | Mean tokens in | Mean tokens out "
        "| p50 generation ms | p95 generation ms | Cost USD (known) | Unknown-cost trials |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    groups = defaultdict(list)
    for trial in trials:
        groups[(trial["arm"], trial["suite"])].append(trial)
    for (arm, suite), rows in sorted(groups.items()):
        generation = [t["timings_ms"].get("generation") for t in rows]
        successes = [t["task_success"] for t in rows if t["task_success"] is not None]
        known_costs = [t["cost"]["usd"] for t in rows if t["cost"]["usd"] is not None]
        lines.append(
            "| " + " | ".join([
                arm, suite, rows[0]["prompt_format"], str(len(rows)),
                str(sum(1 for t in rows if t["error"])),
                _fmt(_mean(t["comprehension_accuracy"] for t in rows)),
                f"{sum(successes)}/{len(successes)}" if successes else "–",
                _fmt(_mean(t["tokens_in"] for t in rows), 1),
                _fmt(_mean(t["tokens_out"] for t in rows), 1),
                _fmt(_percentile(generation, 0.50), 1),
                _fmt(_percentile(generation, 0.95), 1),
                _fmt(sum(known_costs), 4) if known_costs else "–",
                str(sum(1 for t in rows if t["cost"]["usd"] is None)),
            ]) + " |"
        )

    arms = [arm["id"] for arm in manifest["arms"]]
    if len(arms) > 1:
        reference = arms[0]
        lines += ["", f"## Paired by case, relative to arm {reference}", ""]
        lines += ["| Arm | Suite | Cases | Mean difference | Interval |", "|---|---|---|---|---|"]
        per_case = defaultdict(list)
        for trial in trials:
            per_case[(trial["arm"], trial["suite"], trial["case_id"])].append(_case_metric(trial))
        case_means = {key: _mean(values) for key, values in per_case.items()}
        for arm in arms[1:]:
            for suite in manifest.get("suites", []):
                diffs = [
                    case_means[(arm, suite, case)] - case_means[(reference, suite, case)]
                    for case in manifest["case_ids"]
                    if case_means.get((arm, suite, case)) is not None and case_means.get((reference, suite, case)) is not None
                ]
                interval = (
                    f"not estimated (fewer than {MIN_CASES_FOR_INTERVALS} cases)"
                    if len(diffs) < MIN_CASES_FOR_INTERVALS
                    else "paired bootstrap not yet implemented"
                )
                lines.append(f"| {arm} | {suite} | {len(diffs)} | {_fmt(_mean(diffs))} | {interval} |")
    return "\n".join(lines) + "\n"


def write_report(run_dir: Path) -> Path:
    path = Path(run_dir) / "report.md"
    path.write_text(build_report(run_dir), encoding="utf-8", newline="\n")
    return path
