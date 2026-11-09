"""bench usefulness compare: pool repeated runs per arm and compare arms paired by task."""
import json
from pathlib import Path

from rosetta_bench.cli import main
from rosetta_bench.usefulness.replicates import compare_arms


def _run(root: Path, name: str, rep: str, outcomes: dict, tokens: int = 100, ms: float = 1000.0) -> Path:
    run = root / name
    run.mkdir(parents=True)
    (run / "manifest.json").write_text(json.dumps({"run_id": name, "schema": "rosetta-bench/usefulness-matrix@1",
                                                   "corpus_digest": "d" * 64, "live": True}), encoding="utf-8")
    lines = []
    for task, ok in outcomes.items():
        lines.append(json.dumps({"arm": f"{rep}+none", "rep": rep, "decider": "none", "task_id": task, "kind": "code",
                                 "success": ok, "generator_tokens_in": tokens, "generator_tokens_out": tokens,
                                 "decision_tokens": 0, "timings_ms": {"total": ms}, "reasoning_tokens_est": tokens // 2}))
    (run / "trials.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return run


def test_compare_pools_samples_per_task_and_reports_paired_intervals(tmp_path: Path):
    tasks = [f"t{i:02d}" for i in range(12)]
    a = [_run(tmp_path, f"a{k}", "R", {t: True for t in tasks}, tokens=50) for k in range(3)]
    b = [_run(tmp_path, f"b{k}", "M", {t: (i % 4 != 0) for i, t in enumerate(tasks)}, tokens=100) for k in range(3)]
    result = compare_arms({"R": a, "M": b}, n_boot=500, seed=1)
    assert result["arms"]["R"]["samples"] == 3 and result["arms"]["R"]["tasks"] == 12
    assert result["arms"]["R"]["accuracy"] == 1.0 and result["arms"]["M"]["accuracy"] == 0.75
    assert result["arms"]["R"]["tokens_per_success"] < result["arms"]["M"]["tokens_per_success"]
    contrast = result["contrasts"]["R vs M"]
    assert contrast["accuracy"]["mean_diff"] == 0.25 and contrast["accuracy"]["ci_low"] > 0
    assert contrast["better"] == 3 and contrast["worse"] == 0


def test_runs_on_different_corpora_are_refused(tmp_path: Path):
    a = _run(tmp_path, "a", "R", {"t1": True})
    b = _run(tmp_path, "b", "M", {"t1": True})
    manifest = json.loads((b / "manifest.json").read_text(encoding="utf-8"))
    manifest["corpus_digest"] = "e" * 64
    (b / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    try:
        compare_arms({"R": [a], "M": [b]})
    except ValueError as exc:
        assert "corpus" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_cli_writes_a_comparison_report(tmp_path: Path):
    tasks = [f"t{i}" for i in range(10)]
    a = _run(tmp_path, "a", "R", {t: True for t in tasks})
    b = _run(tmp_path, "b", "M", {t: i > 2 for i, t in enumerate(tasks)})
    out = tmp_path / "cmp.md"
    assert main(["usefulness", "compare", "--arm", f"R={a}", "--arm", f"M={b}", "--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert "R vs M" in text and "95% CI" in text and "items needed" in text
