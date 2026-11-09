"""Decision-quality report for a shadow run. Policy-independent metrics (top-1 route
accuracy, Brier score of route_fits) are reported next to the policy's outcomes, so a
poor threshold is not confused with a poor provider."""
import json
from collections import Counter, defaultdict
from pathlib import Path


def _lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.exists() else []


def _pct(numerator: int, denominator: int) -> str:
    return f"{numerator}/{denominator} ({100 * numerator / denominator:.0f}%)" if denominator else "0/0"


def _percentile(values, fraction):
    values = sorted(values)
    if not values:
        return None
    rank = max(1, -(-int(fraction * 100) * len(values) // 100))
    return values[min(rank, len(values)) - 1]


def build_decision_report(run_dir: Path) -> str:
    run_dir = Path(run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    decisions = _lines(run_dir / "decisions.jsonl")
    lines = [f"# Decision run {manifest['run_id']}", ""]
    if manifest["synthetic"]:
        lines += ["> **SYNTHETIC: wiring check only.** The provider was an offline keyword-overlap fake, not a "
                  "decision model. These figures are not evidence about Jev, clef or any provider.", ""]
    provider = manifest["provider"]
    lines += [
        f"- Provider: `{provider['profile']}` requesting `{provider['requested_model']}`; live: {manifest['live']}",
        f"- Policy: `{manifest['policy']['policy_id']}` {manifest['policy']['version']}, calibrated: "
        f"{manifest['policy']['calibrated']}, thresholds {manifest['policy']['thresholds']}",
        f"- Question set hash: `{manifest['question_set']['hash'][:16]}…`",
        f"- Cases: {len(decisions)}; stopped early: {manifest.get('stopped_early') or 'no'}",
        (f"- Cache: {manifest['cache']['hits']} hits, {manifest['cache']['misses']} misses; "
         f"about {manifest['cache']['tokens_avoided']:,} decision input tokens avoided"
         if manifest.get("cache") else "- Cache: off"),
        (f"- Batching: {manifest['batching']['size']} requests per call (question set {manifest['batching']['call_question_set']['version']}, "
         "separate calibration needed)" if manifest.get("batching") else "- Batching: off (one request per call)"),
        "- Labels: authored for wiring, not independently reviewed. Smoke cases establish wiring, not performance.",
        "",
        "## Outcomes",
        "",
        "| Outcome | Count |",
        "|---|---|",
    ]
    for outcome, count in sorted(Counter(d["outcome"] for d in decisions).items()):
        lines.append(f"| {outcome} | {count} |")

    called = [d for d in decisions if d["answers"]]
    top1 = [d for d in called if d["label_fits"] and d["label_route"] in d["eligible_routes"]]
    top1_correct = sum(1 for d in top1 if d["answers"].get("workflow_route", {}).get("selected") == d["label_route"])
    fit_pairs = [(d["answers"]["route_fits"]["p_yes"], 1.0 if d["label_fits"] else 0.0)
                 for d in called if isinstance(d["answers"].get("route_fits", {}).get("p_yes"), (int, float))]
    brier = sum((p - y) ** 2 for p, y in fit_pairs) / len(fit_pairs) if fit_pairs else None
    accepted = [d for d in decisions if d["outcome"] == "ACCEPT"]
    no_fit_cases = [d for d in decisions if not d["label_fits"] and d["outcome"] != "DENY"]
    fits_cases = [d for d in decisions if d["label_fits"] and d["outcome"] != "DENY"]
    latencies = [d["decision_ms"] for d in called]
    tokens = [d["input_tokens"] for d in called if d["input_tokens"] is not None]

    lines += [
        "",
        "## Decision quality",
        "",
        f"- Top-1 route choice vs label (fits cases with an eligible labelled route, ignoring thresholds): {_pct(top1_correct, len(top1))}",
        f"- Brier score of `route_fits` vs label: {brier:.4f} over {len(fit_pairs)} cases" if brier is not None else "- Brier score: n/a",
        f"- Accepted routes matching the label: {_pct(sum(1 for d in accepted if d['route'] == d['label_route']), len(accepted))}",
        f"- Coverage (ACCEPT among labelled-fit cases): {_pct(sum(1 for d in fits_cases if d['outcome'] == 'ACCEPT'), len(fits_cases))}",
        f"- No-fit recall (NO_FIT among labelled no-fit cases): {_pct(sum(1 for d in no_fit_cases if d['outcome'] == 'NO_FIT'), len(no_fit_cases))}",
        f"- False accepts on no-fit cases: {_pct(sum(1 for d in no_fit_cases if d['outcome'] == 'ACCEPT'), len(no_fit_cases))}",
        f"- Abstentions: {sum(1 for d in decisions if d['outcome'] == 'ABSTAIN')}; fallbacks: {sum(1 for d in decisions if d['outcome'] == 'FALLBACK')}",
        "",
        "## By category",
        "",
        "| Category | Cases | ACCEPT | correct ACCEPT | NO_FIT | ABSTAIN | FALLBACK | DENY |",
        "|---|---|---|---|---|---|---|---|",
    ]
    groups = defaultdict(list)
    for d in decisions:
        groups[d["category"]].append(d)
    for category, rows in sorted(groups.items()):
        count = Counter(r["outcome"] for r in rows)
        correct = sum(1 for r in rows if r["outcome"] == "ACCEPT" and r["route"] == r["label_route"])
        lines.append(f"| {category} | {len(rows)} | {count['ACCEPT']} | {correct} | {count['NO_FIT']} | {count['ABSTAIN']} | {count['FALLBACK']} | {count['DENY']} |")

    lines += ["", "## By language", "", "| Language | Cases | correct ACCEPT | NO_FIT |", "|---|---|---|---|"]
    by_language = defaultdict(list)
    for d in decisions:
        by_language[d["language"]].append(d)
    for language, rows in sorted(by_language.items()):
        correct = sum(1 for r in rows if r["outcome"] == "ACCEPT" and r["route"] == r["label_route"])
        lines.append(f"| {language} | {len(rows)} | {correct} | {sum(1 for r in rows if r['outcome'] == 'NO_FIT')} |")

    errors = Counter(d["provider_error"]["kind"] for d in decisions if d["provider_error"])
    lines += [
        "",
        "## Economics and reliability",
        "",
        f"- Provider calls: {sum(d['calls'] for d in decisions)}; transport retries: {sum(d['transport_retries'] for d in decisions)}",
        f"- Decision input tokens: {sum(tokens)} over {len(tokens)} answered cases" + ("" if len(tokens) == len(called) else " (some unknown)"),
        f"- Decision latency p50 / p95 ms: {_percentile(latencies, 0.5)} / {_percentile(latencies, 0.95)}" if latencies else "- Decision latency: n/a",
        f"- Provider errors: {dict(errors) if errors else 'none'}",
        f"- Validation violations: {sum(len(d['violations']) for d in decisions)}",
    ]
    return "\n".join(lines) + "\n"


def write_decision_report(run_dir: Path) -> Path:
    path = Path(run_dir) / "decision_report.md"
    path.write_text(build_decision_report(run_dir), encoding="utf-8", newline="\n")
    return path
