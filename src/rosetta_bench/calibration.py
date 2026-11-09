"""Calibrated abstention for yes/no decision questions, with a risk bound per direction.

A "yes" lets work proceed, so a wrong yes (gold no) is a false pass: the dangerous error. The
yes-threshold is chosen so that the Clopper-Pearson upper bound on the false-pass rate among
yes-decisions is at most alpha; the no-threshold bounds the over-refusal rate the same way. Every
grid threshold is tested at delta / (grid size) (Bonferroni), so the guarantee holds for the
chosen one ("learn then test"; cf. Jung et al., Trust or Escalate, arXiv:2407.18370). Thresholds
are fitted on some item families and checked on held-out families.
"""
from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from pathlib import Path

YES_GRID = [round(0.5 + 0.025 * i, 3) for i in range(21)]  # 0.50 .. 1.00
NO_GRID = [round(0.5 - 0.025 * i, 3) for i in range(21)]  # 0.50 .. 0.00
NEVER_YES, NEVER_NO = 1.01, -0.01


@dataclass(frozen=True)
class Point:
    item: str
    family: str
    question: str
    language: str
    p_yes: float
    gold: bool


@dataclass(frozen=True)
class Fit:
    t_yes: float
    t_no: float
    false_pass_upper: float
    over_refusal_upper: float
    coverage: float
    note: str = ""


def _binom_cdf(k: int, n: int, p: float) -> float:
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))


def clopper_pearson_upper(k: int, n: int, delta: float) -> float:
    """One-sided (1 - delta) upper confidence bound on a binomial rate with k errors in n."""
    if n == 0 or k >= n:
        return 1.0
    low, high = k / n, 1.0
    for _ in range(80):
        mid = (low + high) / 2
        if _binom_cdf(k, n, mid) > delta:
            low = mid
        else:
            high = mid
    return high


def _decide(p: float, t_yes: float, t_no: float) -> str:
    if p >= t_yes:
        return "yes"
    if p <= t_no:
        return "no"
    return "abstain"


def evaluate(points: list[Point], t_yes: float, t_no: float) -> dict:
    verdicts = [(_decide(p.p_yes, t_yes, t_no), p.gold) for p in points]
    decided = [(v, g) for v, g in verdicts if v != "abstain"]
    errors = sum((v == "yes") != g for v, g in decided)
    return {
        "t_yes": t_yes, "t_no": t_no, "n": len(points), "decided": len(decided),
        "coverage": len(decided) / len(points) if points else 0.0,
        "risk": errors / len(decided) if decided else 0.0,
        "false_passes": sum(v == "yes" and not g for v, g in decided),
        "over_refusals": sum(v == "no" and g for v, g in decided),
    }


def risk_coverage(points: list[Point], thresholds: list[float]) -> list[dict]:
    """Symmetric sweep: yes at p >= t, no at p <= 1 - t."""
    return [evaluate(points, t, round(1 - t, 6)) for t in thresholds]


def fit_thresholds(points: list[Point], alpha: float, delta: float) -> Fit:
    level = delta / (len(YES_GRID) + len(NO_GRID))
    t_yes, fp_upper = NEVER_YES, 0.0
    for t in sorted(YES_GRID):  # lowest passing threshold = most coverage
        yes = [p for p in points if p.p_yes >= t]
        upper = clopper_pearson_upper(sum(not p.gold for p in yes), len(yes), level)
        if yes and upper <= alpha:
            t_yes, fp_upper = t, upper
            break
    t_no, or_upper = NEVER_NO, 0.0
    for t in sorted(NO_GRID, reverse=True):
        no = [p for p in points if p.p_yes <= t and p.p_yes < t_yes]
        upper = clopper_pearson_upper(sum(p.gold for p in no), len(no), level)
        if no and upper <= alpha:
            t_no, or_upper = t, upper
            break
    coverage = evaluate(points, t_yes, t_no)["coverage"]
    note = ""
    if t_yes == NEVER_YES or t_no == NEVER_NO:
        note = (f"insufficient data to certify risk <= {alpha} at confidence {1 - delta} for "
                + ", ".join(side for side, t in (("yes", t_yes), ("no", t_no)) if t in (NEVER_YES, NEVER_NO))
                + "; that side always abstains")
    return Fit(t_yes, t_no, fp_upper, or_upper, coverage, note)


def split_by_family(points: list[Point], seed: int, fraction: float = 0.5) -> tuple[list[Point], list[Point]]:
    families = sorted({p.family for p in points})
    random.Random(seed).shuffle(families)
    calibration = set(families[: round(len(families) * fraction)])
    return [p for p in points if p.family in calibration], [p for p in points if p.family not in calibration]


def load_points(runs: list[Path], question: str) -> list[Point]:
    points = []
    for run in runs:
        for line in (Path(run) / "decisions.jsonl").read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            answer = (row.get("questions") or {}).get(question)
            if not answer or answer.get("p_yes") is None or answer.get("gold") is None:
                continue
            points.append(Point(row["item_id"], row.get("family") or row["item_id"], question,
                                row.get("language", "?"), float(answer["p_yes"]), bool(answer["gold"])))
    return points


def calibrate(runs: list[Path], question: str, alpha: float, delta: float, seed: int = 0) -> dict:
    points = load_points(runs, question)
    calibration, held_out = split_by_family(points, seed)
    fit = fit_thresholds(calibration, alpha, delta)
    return {
        "question": question, "alpha": alpha, "delta": delta, "seed": seed,
        "items": {"calibration": len(calibration), "held_out": len(held_out)},
        "thresholds": {"t_yes": fit.t_yes, "t_no": fit.t_no},
        "calibration": {**evaluate(calibration, fit.t_yes, fit.t_no), "false_pass_upper": fit.false_pass_upper,
                        "over_refusal_upper": fit.over_refusal_upper, "note": fit.note},
        "held_out": evaluate(held_out, fit.t_yes, fit.t_no),
        "placeholder_held_out": evaluate(held_out, 0.7, 0.3),
        "curve": risk_coverage(points, YES_GRID),
    }


def render_calibration(result: dict) -> str:
    c, h, ph = result["calibration"], result["held_out"], result["placeholder_held_out"]
    lines = [
        f"# Calibrated abstention: `{result['question']}`", "",
        f"Target: false-pass and over-refusal rates each at most {result['alpha']} with confidence {1 - result['delta']} "
        f"(Clopper-Pearson, Bonferroni over the threshold grid). Families split {result['items']['calibration']} / "
        f"{result['items']['held_out']} items (seed {result['seed']}).", "",
        f"- Thresholds: yes at p >= {result['thresholds']['t_yes']}, no at p <= {result['thresholds']['t_no']}"
        + (f" ({c['note']})" if c["note"] else ""),
        f"- Calibration bounds: false pass <= {c['false_pass_upper']:.3f}, over-refusal <= {c['over_refusal_upper']:.3f}", "",
        "| Set | Items | Decided | Coverage | Error rate | False passes | Over-refusals |", "|---|---|---|---|---|---|---|",
    ]
    for name, row in (("Calibration", c), ("Held-out", h), ("Held-out at placeholder 0.7 / 0.3", ph)):
        lines.append(f"| {name} | {row['n']} | {row['decided']} | {row['coverage']:.2f} | {row['risk']:.3f} | "
                     f"{row['false_passes']} | {row['over_refusals']} |")
    lines += ["", "## Risk-coverage curve (all items, symmetric thresholds)", "",
              "| yes at p >= | no at p <= | Coverage | Error rate | False passes |", "|---|---|---|---|---|"]
    for row in result["curve"]:
        lines.append(f"| {row['t_yes']} | {row['t_no']} | {row['coverage']:.2f} | {row['risk']:.3f} | {row['false_passes']} |")
    return "\n".join(lines) + "\n"
