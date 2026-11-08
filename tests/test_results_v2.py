from pathlib import Path

import pytest

from rosetta_bench.models import Trial
from rosetta_bench.results_v2 import (
    ManifestInvalid,
    RunWriter,
    load_legacy_trials,
    load_manifest,
    load_trials_v2,
)
from rosetta_bench.storage import append_trial


def _manifest(**overrides) -> dict:
    manifest = {
        "schema": "rosetta-bench/run-manifest@1",
        "run_id": "run-1",
        "created_at": "2026-11-09T12:00:00Z",
        "experiment": "smoke-offline",
        "synthetic": True,
        "seed": 7,
        "arms": [{"id": "A"}],
        "case_ids": ["rosetta_build"],
        "trial_order": ["t1"],
        "repos": {"bench": None, "core": None},
        "environment": {"python": "3.14"},
    }
    manifest.update(overrides)
    return manifest


def test_writer_creates_manifest_and_appends_trials(tmp_path: Path):
    writer = RunWriter(tmp_path / "run")
    writer.write_manifest(_manifest())
    writer.append_trial({"trial_id": "t1", "cost": {"usd": None, "basis": "unknown"}})
    writer.append_trial({"trial_id": "t2", "cost": {"usd": 0.0, "basis": "free_local"}})

    assert load_manifest(tmp_path / "run")["run_id"] == "run-1"
    trials = load_trials_v2(tmp_path / "run")
    assert [t["trial_id"] for t in trials] == ["t1", "t2"]
    assert trials[0]["cost"]["usd"] is None


def test_writer_refuses_to_reuse_an_existing_run_directory(tmp_path: Path):
    (tmp_path / "run").mkdir()
    (tmp_path / "run" / "manifest.json").write_text("{}", encoding="utf-8")
    with pytest.raises(FileExistsError):
        RunWriter(tmp_path / "run")


def test_manifest_must_carry_its_required_keys(tmp_path: Path):
    manifest = _manifest()
    del manifest["synthetic"]
    with pytest.raises(ManifestInvalid):
        RunWriter(tmp_path / "run").write_manifest(manifest)


def _legacy_trial(trial_id: str, cost_usd: float) -> Trial:
    return Trial(
        trial_id=trial_id, timestamp="2026-07-13T00:00:00Z", tool="CLAUDE", model="m1",
        prompt_id="rosetta_build", prompt_format="MACHINE", suite="TASK_COMPLETION",
        tokens_in=10, tokens_out=5, latency_ms=100.0, turns=1, task_success=None,
        comprehension_accuracy=None, quality_score=4.0, judge_justification="ok",
        cost_usd=cost_usd, raw_output="output",
    )


def test_legacy_csv_rows_are_read_with_an_unverified_cost_basis(tmp_path: Path):
    path = tmp_path / "trials.csv"
    append_trial(_legacy_trial("t1", 0.01), path)
    rows = load_legacy_trials(path)
    assert rows[0]["schema"] == "rosetta-bench/trial@legacy-csv"
    assert rows[0]["cost"] == {"usd": 0.01, "basis": "legacy_unverified", "price_source": None, "price_as_of": None}


def test_legacy_zero_cost_is_not_reinterpreted_as_free(tmp_path: Path):
    path = tmp_path / "trials.csv"
    append_trial(_legacy_trial("t1", 0.0), path)
    cost = load_legacy_trials(path)[0]["cost"]
    assert cost["usd"] == 0.0
    assert cost["basis"] == "legacy_unverified"
