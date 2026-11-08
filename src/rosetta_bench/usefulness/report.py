"""Usefulness report for a representation x decision matrix run.

Verified success comes first (hidden tests for code tasks; no code for no-code requests),
then what it cost: tokens (generator + decision) and attributed time. Contrasts are paired
by task. No uncertainty intervals are estimated below 10 paired tasks."""
import json
from collections import defaultdict
from pathlib import Path

MIN_TASKS_FOR_INTERVALS = 10


def _lines(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()] if path.exists() else []


def _pct(values, q):
    values = sorted(v for v in values if v is not None)
    if not values:
        return None
    return values[max(1, -(-int(q * 100) * len(values) // 100)) - 1]


def arm_metrics(rows: list[dict]) -> dict:
    code = [r for r in rows if r["kind"] == "code"]
    no_code = [r for r in rows if r["kind"] == "no_code"]
    declined = [r for r in rows if r["declined_by"] == "decision"]
    successes = sum(r["success"] for r in rows)
    tokens = sum(r["generator_tokens_in"] + r["generator_tokens_out"] + r["decision_tokens"] for r in rows)
    totals = [r["timings_ms"].get("total") for r in rows]
    return {
        "n": len(rows),
        "successes": successes,
        "accuracy": successes / len(rows) if rows else None,
        "code_passed": sum(r["success"] for r in code), "code_n": len(code),
        "no_code_handled": sum(r["success"] for r in no_code), "no_code_n": len(no_code),
        "decline_precision": (sum(r["kind"] == "no_code" for r in declined) / len(declined)) if declined else None,
        "decline_recall": (sum(1 for r in declined if r["kind"] == "no_code") / len(no_code)) if no_code else None,
        "code_routed_to_code": (sum(r["route"] == "code_change" for r in code) / len(code)) if code else None,
        "generator_calls_charged": sum(r["generated"] for r in rows),
        "generator_tokens": sum(r["generator_tokens_in"] + r["generator_tokens_out"] for r in rows),
        "decision_tokens": sum(r["decision_tokens"] for r in rows),
        "tokens": tokens,
        "tokens_per_success": tokens / successes if successes else None,
        "p50_ms": _pct(totals, 0.5), "p95_ms": _pct(totals, 0.95),
        "errors": sum(1 for r in rows if r["error"]),
        "timeouts": sum(1 for r in rows if r["sandbox"] and r["sandbox"]["timed_out"]),
    }


def _f(value, digits=0, pct=False):
    if value is None:
        return "–"
    if pct:
        return f"{100 * value:.0f}%"
    return f"{value:,.{digits}f}"


def _paired(a_rows, b_rows):
    a = {r["task_id"]: r for r in a_rows}
    b = {r["task_id"]: r for r in b_rows}
    shared = sorted(set(a) & set(b))
    better = sum(a[t]["success"] and not b[t]["success"] for t in shared)
    worse = sum(b[t]["success"] and not a[t]["success"] for t in shared)
    return shared, better, worse


def _contrast_row(label, a_rows, b_rows):
    shared, better, worse = _paired(a_rows, b_rows)
    ma, mb = arm_metrics(a_rows), arm_metrics(b_rows)
    d_acc = None if ma["accuracy"] is None or mb["accuracy"] is None else ma["accuracy"] - mb["accuracy"]
    d_tok = None if not ma["tokens_per_success"] or not mb["tokens_per_success"] else ma["tokens_per_success"] / mb["tokens_per_success"] - 1
    d_p50 = None if not ma["p50_ms"] or not mb["p50_ms"] else ma["p50_ms"] / mb["p50_ms"] - 1
    note = "" if len(shared) >= MIN_TASKS_FOR_INTERVALS else " (too few tasks for an interval)"
    return (f"| {label} | {len(shared)} | {better} | {worse} | {_f(d_acc * 100 if d_acc is not None else None, 1)} pp "
            f"| {_f(d_tok, pct=True)} | {_f(d_p50, pct=True)} |{note}")


def build_usefulness_report(run_dir: Path) -> str:
    run_dir = Path(run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    trials = _lines(run_dir / "trials.jsonl")
    decisions = _lines(run_dir / "decisions.jsonl")
    by_arm = defaultdict(list)
    for trial in trials:
        by_arm[(trial["rep"], trial["decider"])].append(trial)
    reps = list(manifest["representations"])
    deciders = manifest["deciders"]
    gen = manifest["generator"]

    lines = [f"# Usefulness matrix {manifest['run_id']}", ""]
    if manifest["synthetic"]:
        lines += ["> **SYNTHETIC: wiring check only.** Offline fakes stood in for the generator and the decision providers. "
                  "These figures describe nothing about any model.", ""]
    lines += [
        f"- Generator: `{gen['kind']}` `{gen['model']}` settings {gen.get('settings', {})}; live: {manifest['live']}",
        f"- Representations: " + "; ".join(f"**{k}** = {v}" for k, v in manifest["representations"].items()),
        f"- Deciders: {', '.join(deciders)}; providers: "
        + (", ".join(f"`{n}` → `{p['requested_model']}` (calibrated: {p['policy']['calibrated']})" for n, p in manifest["providers"].items()) or "none"),
        f"- Trials: {len(trials)}; stopped early: {manifest.get('stopped_early') or 'no'}",
        f"- Accounting: {manifest['accounting']}",
        "",
        "## Matrix",
        "",
        "Each cell: verified successes / trials · tokens per verified success · p50 attributed ms.",
        "",
        "| Representation | " + " | ".join(deciders) + " |",
        "|---|" + "---|" * len(deciders),
    ]
    for rep in reps:
        cells = []
        for decider in deciders:
            m = arm_metrics(by_arm.get((rep, decider), []))
            cells.append(f"{m['successes']}/{m['n']} · {_f(m['tokens_per_success'])} · {_f(m['p50_ms'])}" if m["n"] else "–")
        lines.append(f"| {rep} | " + " | ".join(cells) + " |")

    lines += [
        "",
        "## Per arm",
        "",
        "| Arm | Trials | Accuracy | Code passed | No-code handled | Decline precision | Decline recall | Code tasks on code route "
        "| Generator calls charged | Generator tokens | Decision tokens | Tokens per verified success | p50 / p95 ms | Errors | Timeouts |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for rep in reps:
        for decider in deciders:
            m = arm_metrics(by_arm.get((rep, decider), []))
            if not m["n"]:
                continue
            lines.append(
                f"| {rep}+{decider} | {m['n']} | {_f(m['accuracy'], pct=True)} | {m['code_passed']}/{m['code_n']} "
                f"| {m['no_code_handled']}/{m['no_code_n']} | {_f(m['decline_precision'], pct=True)} | {_f(m['decline_recall'], pct=True)} "
                f"| {_f(m['code_routed_to_code'], pct=True)} | {m['generator_calls_charged']} | {_f(m['generator_tokens'])} "
                f"| {_f(m['decision_tokens'])} | {_f(m['tokens_per_success'])} | {_f(m['p50_ms'])} / {_f(m['p95_ms'])} | {m['errors']} | {m['timeouts']} |"
            )

    header = ["| Contrast (A vs B) | Paired tasks | A better | B better | Accuracy A−B | Tokens/success A vs B | p50 A vs B |",
              "|---|---|---|---|---|---|---|"]
    lines += ["", "## Representation contrasts", "", "Plain prompt (P) against Rosetta (H, M), within each decision mode.", ""] + header
    for decider in deciders:
        for a, b in (("P", "H"), ("P", "M"), ("H", "M")):
            if (a, decider) in by_arm and (b, decider) in by_arm:
                lines.append(_contrast_row(f"{a} vs {b} · {decider}", by_arm[(a, decider)], by_arm[(b, decider)]))

    providers = [d for d in deciders if d not in ("none", "consensus")]
    pairs = [("none", p) for p in providers] + ([("none", "consensus")] if "consensus" in deciders else [])
    pairs += [(providers[i], providers[j]) for i in range(len(providers)) for j in range(i + 1, len(providers))]
    pairs += [(p, "consensus") for p in providers] if "consensus" in deciders else []
    lines += ["", "## Decision contrasts", "", "Without and with each decision layer, within each representation.", ""] + header
    for rep in reps:
        for a, b in pairs:
            if (rep, a) in by_arm and (rep, b) in by_arm:
                lines.append(_contrast_row(f"{a} vs {b} · {rep}", by_arm[(rep, a)], by_arm[(rep, b)]))

    if decisions:
        lines += ["", "## Decision providers on these tasks", "",
                  "| Provider | Tasks | ACCEPT | NO_FIT | ABSTAIN | FALLBACK | Code→code_change | No-code→NO_FIT | Tokens | p50 ms |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
        by_provider = defaultdict(list)
        for d in decisions:
            by_provider[d["provider"]].append(d)
        for provider, rows in sorted(by_provider.items()):
            count = lambda o: sum(r["outcome"] == o for r in rows)
            code = [r for r in rows if r["kind"] == "code"]
            no_code = [r for r in rows if r["kind"] == "no_code"]
            lines.append(
                f"| {provider} | {len(rows)} | {count('ACCEPT')} | {count('NO_FIT')} | {count('ABSTAIN')} | {count('FALLBACK')} "
                f"| {sum(r['route'] == 'code_change' for r in code)}/{len(code)} | {sum(r['outcome'] == 'NO_FIT' for r in no_code)}/{len(no_code)} "
                f"| {sum(r['input_tokens'] for r in rows):,} | {_f(_pct([r['decision_ms'] for r in rows], 0.5))} |"
            )

    checked = [t for t in trials if t["postflight"] and t["postflight"]["addresses_task"] is not None and t["kind"] == "code"]
    if checked:
        lines += ["", "## Postflight (advisory)", "", "| Provider | Code checked | Mean p on passing code | Mean p on failing code | Failing flagged (p<0.5) | Passing flagged |",
                  "|---|---|---|---|---|---|"]
        by_decider = defaultdict(list)
        for t in checked:
            by_decider[t["decider"]].append(t)
        mean = lambda xs: f"{sum(xs) / len(xs):.3f}" if xs else "–"
        for decider, rows in sorted(by_decider.items()):
            passed = [r["postflight"]["addresses_task"] for r in rows if r["success"]]
            failed = [r["postflight"]["addresses_task"] for r in rows if not r["success"]]
            lines.append(f"| {decider} | {len(rows)} | {mean(passed)} | {mean(failed)} | {sum(p < 0.5 for p in failed)}/{len(failed)} "
                         f"| {sum(p < 0.5 for p in passed)}/{len(passed)} |")
    return "\n".join(lines) + "\n"


def write_usefulness_report(run_dir: Path) -> Path:
    path = Path(run_dir) / "usefulness_report.md"
    path.write_text(build_usefulness_report(run_dir), encoding="utf-8", newline="\n")
    return path
