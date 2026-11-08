"""Usefulness report: verified success first, then the tokens and latency it cost.
Tokens per verified success counts generator and decision tokens together."""
import json
from collections import defaultdict
from pathlib import Path


def _lines(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()] if path.exists() else []


def _pct(values, q):
    values = sorted(v for v in values if v is not None)
    if not values:
        return None
    return values[max(1, -(-int(q * 100) * len(values) // 100)) - 1]


def build_usefulness_report(run_dir: Path) -> str:
    run_dir = Path(run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    trials = _lines(run_dir / "trials.jsonl")
    lines = [f"# Usefulness run {manifest['run_id']}", ""]
    if manifest["synthetic"]:
        lines += ["> **SYNTHETIC: wiring check only.** The generator (and decision provider, if any) were offline fakes. "
                  "These figures are not evidence about any model.", ""]
    generator = manifest["generator"]
    decision = manifest.get("decision")
    lines += [
        f"- Generator: `{generator['kind']}` `{generator['model']}` settings {generator.get('settings', {})}; live: {manifest['live']}",
        f"- Decision: {('`' + decision['profile'] + '` (policy calibrated: ' + str(decision['policy']['calibrated']) + ')') if decision else 'none'}",
        f"- Trials: {len(trials)}; stopped early: {manifest.get('stopped_early') or 'no'}",
        "- Small task counts: no uncertainty intervals are estimated below 10 paired tasks.",
        "",
        "## Per arm",
        "",
        "| Arm | Trials | Code tasks passed | No-code handled | Verified successes | Generator calls | Generator tokens (in/out) "
        "| Decision tokens | Tokens per verified success | p50 / p95 total ms | Sandbox timeouts | Errors |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    by_arm = defaultdict(list)
    for trial in trials:
        by_arm[trial["arm"]].append(trial)
    for arm in sorted(by_arm):
        rows = by_arm[arm]
        code = [r for r in rows if r["kind"] == "code"]
        no_code = [r for r in rows if r["kind"] == "no_code"]
        successes = sum(r["success"] for r in rows)
        gen_in = sum(r["generator_tokens_in"] for r in rows)
        gen_out = sum(r["generator_tokens_out"] for r in rows)
        dec = sum(r["decision_tokens"] for r in rows)
        per_success = f"{(gen_in + gen_out + dec) / successes:,.0f}" if successes else "–"
        totals = [r["timings_ms"].get("total") for r in rows]
        p50, p95 = _pct(totals, 0.5), _pct(totals, 0.95)
        lines.append(
            f"| {arm} | {len(rows)} | {sum(r['success'] for r in code)}/{len(code)} | {sum(r['success'] for r in no_code)}/{len(no_code)} "
            f"| {successes} | {sum(r['generated'] for r in rows)} | {gen_in:,} / {gen_out:,} | {dec:,} | {per_success} "
            f"| {p50:,.0f} / {p95:,.0f} | {sum(1 for r in rows if r['sandbox'] and r['sandbox']['timed_out'])} "
            f"| {sum(1 for r in rows if r['error'])} |" if p50 is not None else f"| {arm} | {len(rows)} | – |"
        )

    if "B" in by_arm:
        lines += ["", "## Paired with arm B, by task", "", "| Arm | Tasks | Better | Worse | Same |", "|---|---|---|---|---|"]
        base = {r["task_id"]: r["success"] for r in by_arm["B"]}
        for arm in sorted(a for a in by_arm if a != "B"):
            pairs = [(r["success"], base[r["task_id"]]) for r in by_arm[arm] if r["task_id"] in base]
            lines.append(f"| {arm} | {len(pairs)} | {sum(a and not b for a, b in pairs)} | {sum(b and not a for a, b in pairs)} "
                         f"| {sum(a == b for a, b in pairs)} |")

    routed = [r for r in trials if r["route_decision"]]
    if routed:
        lines += ["", "## Decision arm", ""]
        outcomes = defaultdict(int)
        for r in routed:
            outcomes[r["route_decision"]["outcome"]] += 1
        lines.append(f"- Intake outcomes: {dict(sorted(outcomes.items()))}")
        lines.append(f"- Declined by decision: {sum(1 for r in routed if r['declined_by'] == 'decision')} "
                     f"(no-code tasks: {sum(1 for r in routed if r['declined_by'] == 'decision' and r['kind'] == 'no_code')}, "
                     f"code tasks wrongly declined: {sum(1 for r in routed if r['declined_by'] == 'decision' and r['kind'] == 'code')})")
        misrouted = [r for r in routed if r["kind"] == "code" and r["route"] not in (None, "code_change")]
        lines.append(f"- Code tasks sent to a non-code route: {len(misrouted)} {[r['task_id'] for r in misrouted] or ''}".rstrip())
        checked = [r for r in routed if r["postflight"] and r["postflight"]["addresses_task"] is not None and r["kind"] == "code"]
        if checked:
            passed = [r["postflight"]["addresses_task"] for r in checked if r["success"]]
            failed = [r["postflight"]["addresses_task"] for r in checked if not r["success"]]
            mean = lambda xs: f"{sum(xs) / len(xs):.3f}" if xs else "–"
            lines += [
                "",
                "### Postflight (advisory)",
                "",
                f"- Mean `addresses_task` on code that passed its tests: {mean(passed)} (n={len(passed)}); on code that failed: {mean(failed)} (n={len(failed)})",
                f"- Flagged (p < 0.5): {sum(p < 0.5 for p in failed)}/{len(failed)} failing, {sum(p < 0.5 for p in passed)}/{len(passed)} passing",
            ]
    return "\n".join(lines) + "\n"


def write_usefulness_report(run_dir: Path) -> Path:
    path = Path(run_dir) / "usefulness_report.md"
    path.write_text(build_usefulness_report(run_dir), encoding="utf-8", newline="\n")
    return path
