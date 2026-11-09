"""Pool repeated usefulness runs per arm and compare arms paired by task.

Each arm is a list of run folders (samples) over the same corpus. Success, tokens and time are
averaged per task first; contrasts bootstrap over tasks (see rosetta_bench.stats)."""
from __future__ import annotations

import json
from pathlib import Path

from rosetta_bench.stats import cluster_means, mcnemar_exact, paired_bootstrap, paired_power

DETECT_DELTA = 0.05  # the accuracy difference we would like to be able to detect


def _lines(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()] if path.exists() else []


def _pct(values, q):
    values = sorted(v for v in values if v is not None)
    if not values:
        return None
    return values[max(1, -(-int(q * 100) * len(values) // 100)) - 1]


def _tokens(trial: dict) -> int:
    return (trial.get("generator_tokens_in") or 0) + (trial.get("generator_tokens_out") or 0) + (trial.get("decision_tokens") or 0)


def compare_arms(groups: dict[str, list[Path]], *, n_boot: int = 10_000, seed: int = 0) -> dict:
    digests = set()
    per_arm: dict[str, dict] = {}
    for label, runs in groups.items():
        success: dict[str, list] = {}
        tokens: dict[str, list] = {}
        trials_all = []
        for run in runs:
            run = Path(run)
            manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
            digests.add(manifest.get("corpus_digest"))
            for trial in _lines(run / "trials.jsonl"):
                trials_all.append(trial)
                success.setdefault(trial["task_id"], []).append(1.0 if trial["success"] else 0.0)
                tokens.setdefault(trial["task_id"], []).append(float(_tokens(trial)))
        total_success = sum(1 for t in trials_all if t["success"])
        per_task = cluster_means(success)
        per_arm[label] = {
            "samples": len(runs),
            "tasks": len(per_task),
            "trials": len(trials_all),
            "accuracy": sum(per_task.values()) / len(per_task) if per_task else None,
            "tokens_per_success": sum(_tokens(t) for t in trials_all) / total_success if total_success else None,
            "reasoning_tokens_mean": (sum(t.get("reasoning_tokens_est") or 0 for t in trials_all) / len(trials_all)) if trials_all else None,
            "p50_ms": _pct([t["timings_ms"].get("total") for t in trials_all], 0.5),
            "p95_ms": _pct([t["timings_ms"].get("total") for t in trials_all], 0.95),
            "_success": success,
            "_tokens": tokens,
        }
    if len(digests) > 1:
        raise ValueError(f"runs use different corpus versions (digests {sorted(d[:12] for d in digests if d)}); not comparable")

    labels = list(groups)
    contrasts = {}
    for i, a in enumerate(labels):
        for b in labels[i + 1:]:
            sa, sb = per_arm[a]["_success"], per_arm[b]["_success"]
            ma, mb = cluster_means(sa), cluster_means(sb)
            shared = sorted(set(ma) & set(mb))
            better = sum(ma[t] > mb[t] for t in shared)
            worse = sum(ma[t] < mb[t] for t in shared)
            majority_a_only = sum(ma[t] > 0.5 >= mb[t] for t in shared)
            majority_b_only = sum(mb[t] > 0.5 >= ma[t] for t in shared)
            discordance = (majority_a_only + majority_b_only) / len(shared) if shared else 0.0
            needed = paired_power(discordance, DETECT_DELTA)
            accuracy = paired_bootstrap(sa, sb, n_boot=n_boot, seed=seed)
            tokens = paired_bootstrap(per_arm[a]["_tokens"], per_arm[b]["_tokens"], n_boot=n_boot, seed=seed)
            contrasts[f"{a} vs {b}"] = {
                "tasks": len(shared), "better": better, "worse": worse,
                "accuracy": accuracy.__dict__, "tokens_per_task": tokens.__dict__,
                "mcnemar_p": mcnemar_exact(majority_a_only, majority_b_only),
                "items_needed_for_5pp": needed,
                "power_ratio": (len(shared) / needed) if needed else None,
            }
    for arm in per_arm.values():
        arm.pop("_success")
        arm.pop("_tokens")
    return {"arms": per_arm, "contrasts": contrasts}


def _f(value, digits=3):
    return "–" if value is None else f"{value:,.{digits}f}"


def render_comparison(result: dict) -> str:
    lines = ["# Arm comparison (paired by task)", "",
             "Samples are averaged per task before comparing; intervals are percentile bootstraps over tasks. "
             "McNemar uses each task's majority outcome (success in more than half of its samples), so a task split "
             "evenly across an even number of samples counts as a failure there but still moves the bootstrap.", "",
             "| Arm | Samples | Tasks | Accuracy | Tokens per verified success | Mean reasoning tokens (est.) | p50 / p95 ms |",
             "|---|---|---|---|---|---|---|"]
    for label, arm in result["arms"].items():
        lines.append(f"| {label} | {arm['samples']} | {arm['tasks']} | {_f(arm['accuracy'])} | {_f(arm['tokens_per_success'], 0)} "
                     f"| {_f(arm['reasoning_tokens_mean'], 0)} | {_f(arm['p50_ms'], 0)} / {_f(arm['p95_ms'], 0)} |")
    lines += ["", "| Contrast | Tasks | A better | B better | Accuracy A−B (95% CI) | Tokens per task A−B (95% CI) "
              "| McNemar p | items needed for 5 pp | have / need |",
              "|---|---|---|---|---|---|---|---|---|"]
    for name, c in result["contrasts"].items():
        acc, tok = c["accuracy"], c["tokens_per_task"]
        acc_ci = "–" if acc["ci_low"] is None else f"{_f(acc['mean_diff'])} ({_f(acc['ci_low'])}, {_f(acc['ci_high'])})"
        tok_ci = "–" if tok["ci_low"] is None else f"{_f(tok['mean_diff'], 0)} ({_f(tok['ci_low'], 0)}, {_f(tok['ci_high'], 0)})"
        lines.append(f"| {name} | {c['tasks']} | {c['better']} | {c['worse']} | {acc_ci} | {tok_ci} | {_f(c['mcnemar_p'])} "
                     f"| {c['items_needed_for_5pp'] or '–'} | {_f(c['power_ratio'], 2)} |")
    return "\n".join(lines) + "\n"
