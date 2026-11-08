from pathlib import Path

import yaml

from rosetta_bench.cli import main
from rosetta_bench.experiment.fakes import FakeGenerator
from rosetta_bench.results_v2 import load_manifest, load_trials_v2

CORPUS = Path(__file__).resolve().parent.parent / "corpus"


def _config(tmp_path: Path, **overrides) -> Path:
    config = {
        "experiment": "smoke-offline",
        "seed": 7,
        "corpus_dir": str(CORPUS),
        "cases": ["rosetta_build"],
        "suites": ["COMPREHENSION", "TASK_COMPLETION"],
        "repeats": 1,
        "arms": [
            {"id": "A", "prompt_format": "HUMAN", "generator": {"kind": "fake", "model": "echo-1"}},
            {"id": "B", "prompt_format": "MACHINE", "generator": {"kind": "fake", "model": "echo-1"}},
        ],
    }
    config.update(overrides)
    path = tmp_path / "experiment.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return path


def test_offline_experiment_runs_from_cli_to_report(tmp_path: Path):
    out = tmp_path / "run"
    assert main(["experiment", "run", "--config", str(_config(tmp_path)), "--out", str(out)]) == 0

    manifest = load_manifest(out)
    assert manifest["synthetic"] is True
    assert [arm["id"] for arm in manifest["arms"]] == ["A", "B"]
    assert len(manifest["trial_order"]) == 4

    trials = load_trials_v2(out)
    assert len(trials) == 4
    assert all(t["synthetic"] is True for t in trials)
    assert all(t["cost"]["basis"] == "free_local" for t in trials)
    assert all("generation" in t["timings_ms"] for t in trials)
    comprehension = [t for t in trials if t["suite"] == "COMPREHENSION"]
    task = [t for t in trials if t["suite"] == "TASK_COMPLETION"]
    assert all(t["comprehension_accuracy"] is not None for t in comprehension)
    assert all(t["task_success"] is not None for t in task)

    assert main(["experiment", "report", "--run", str(out)]) == 0
    report = (out / "report.md").read_text(encoding="utf-8")
    assert "SYNTHETIC" in report
    assert "| A |" in report and "| B |" in report


def test_trial_order_is_reproducible_from_the_seed(tmp_path: Path):
    config = _config(tmp_path)
    assert main(["experiment", "run", "--config", str(config), "--out", str(tmp_path / "r1")]) == 0
    assert main(["experiment", "run", "--config", str(config), "--out", str(tmp_path / "r2")]) == 0
    order = lambda run: [t.split(":", 1)[1] for t in load_manifest(tmp_path / run)["trial_order"]]
    assert order("r1") == order("r2")


def test_live_generators_are_refused_in_an_offline_run(tmp_path: Path, capsys):
    arms = [{"id": "B", "prompt_format": "MACHINE", "generator": {"kind": "ollama", "model": "kimi-k2.7-code:cloud"}}]
    code = main(["experiment", "run", "--config", str(_config(tmp_path, arms=arms)), "--out", str(tmp_path / "run")])
    assert code == 2
    assert "offline" in capsys.readouterr().err.lower()
    assert not (tmp_path / "run").exists()


def test_an_existing_run_directory_is_not_overwritten(tmp_path: Path, capsys):
    out = tmp_path / "run"
    assert main(["experiment", "run", "--config", str(_config(tmp_path)), "--out", str(out)]) == 0
    assert main(["experiment", "run", "--config", str(_config(tmp_path)), "--out", str(out)]) == 2
    assert "exists" in capsys.readouterr().err.lower()


def test_fake_generator_reads_values_from_either_format():
    questions = "\n\n1. What is TASK?"
    fake = FakeGenerator("echo-1")
    assert fake.run("SCHEMA_VER=1.0\nTASK=ROSETTA_BUILD\n" + questions, None).raw_output == "1. ROSETTA_BUILD"
    assert fake.run("# Doc\n- TASK: ROSETTA_BUILD\n" + questions, None).raw_output == "1. ROSETTA_BUILD"
