import json
from pathlib import Path

import pytest

from rosetta_bench.calibration import (
    Point,
    clopper_pearson_upper,
    fit_thresholds,
    load_points,
    risk_coverage,
    split_by_family,
)
from rosetta_bench.cli import main


def test_clopper_pearson_upper_matches_known_values():
    assert clopper_pearson_upper(0, 10, 0.05) == pytest.approx(1 - 0.05 ** (1 / 10), abs=1e-6)  # 0.2589
    assert clopper_pearson_upper(10, 10, 0.05) == 1.0
    assert 0.2 < clopper_pearson_upper(2, 20, 0.05) < 0.35


def _points(n_per_side=40, n_errors=3):
    points = []
    for i in range(n_per_side):  # gold True: p spread high; gold False: p spread low, with some confident errors
        points.append(Point(f"t{i}", f"f{i}", "q", "en", 0.55 + 0.45 * i / n_per_side, True))
        p = 0.45 - 0.45 * i / n_per_side
        if i < n_errors:
            p = 0.92  # confident wrong "yes" on a gold-False item: a false pass
        points.append(Point(f"n{i}", f"g{i}", "q", "en", p, False))
    return points


def test_risk_coverage_counts_decisions_errors_and_false_passes():
    curve = risk_coverage(_points(), [0.5, 0.95])
    loose, strict = curve[0], curve[1]
    assert loose["coverage"] == 1.0 and loose["false_passes"] == 3
    assert strict["coverage"] < loose["coverage"] and strict["false_passes"] == 0


def test_fit_bounds_the_false_pass_rate_on_the_calibration_set():
    # 60 confident errors make any threshold at or below 0.92 exceed a 20% false-pass rate
    fit = fit_thresholds(_points(200, n_errors=60), alpha=0.2, delta=0.1)
    assert 0.92 < fit.t_yes <= 1.0  # a real threshold, above the confident errors
    assert 0.0 <= fit.t_no < 0.55
    assert fit.false_pass_upper <= 0.2 and fit.over_refusal_upper <= 0.2
    assert fit.coverage > 0.4
    # a few rare errors do not force the threshold up: their rate is already within the bound
    assert fit_thresholds(_points(200, n_errors=3), alpha=0.2, delta=0.1).t_yes == 0.5


def test_fit_abstains_entirely_when_the_data_cannot_support_the_bound():
    few = [Point("a", "fa", "q", "en", 0.9, True), Point("b", "fb", "q", "en", 0.1, False)]
    fit = fit_thresholds(few, alpha=0.05, delta=0.05)
    assert fit.t_yes > 1.0 and fit.t_no < 0.0  # never decide: two items cannot certify 5% risk
    assert "insufficient" in fit.note


def test_split_by_family_keeps_families_together_and_is_reproducible():
    points = _points()
    cal, held = split_by_family(points, seed=4)
    assert {p.family for p in cal}.isdisjoint({p.family for p in held})
    assert split_by_family(points, seed=4) == (cal, held)


def _eval_run(root: Path) -> Path:
    run = root / "eval"
    run.mkdir()
    (run / "manifest.json").write_text(json.dumps({"schema": "rosetta-bench/decision-eval@1", "run_id": "e1"}), encoding="utf-8")
    rows = []
    for i, p in enumerate(_points()):
        rows.append({"item_id": p.item, "family": p.family, "language": p.language,
                     "questions": {"task_feasible": {"gold": p.gold, "p_yes": p.p_yes}}})
    (run / "decisions.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return run


def test_load_points_reads_a_decision_eval_run(tmp_path: Path):
    points = load_points([_eval_run(tmp_path)], "task_feasible")
    assert len(points) == 80 and all(isinstance(p.gold, bool) for p in points)


def test_cli_writes_thresholds_and_held_out_results(tmp_path: Path):
    run = _eval_run(tmp_path)
    out = tmp_path / "cal.md"
    assert main(["decision", "calibrate", "--run", str(run), "--question", "task_feasible", "--alpha", "0.2",
                 "--delta", "0.1", "--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert "Held-out" in text and "risk-coverage" in text.lower()
    assert json.loads(out.with_suffix(".json").read_text(encoding="utf-8"))["thresholds"]["t_yes"] > 0.5
