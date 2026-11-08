import json
import sqlite3
from pathlib import Path

import pytest

pytest.importorskip("rosetta_core.decision", reason="catalog tests need rosetta-core installed")

from rosetta_bench.catalog import build_db, log_run, run_kind, summarize_run
from rosetta_bench.cli import main

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def results(tmp_path: Path) -> Path:
    from rosetta_bench.usefulness import pipeline
    from test_usefulness import FakeSandbox

    runs = tmp_path / "results" / "runs"
    assert main(["decision", "run", "--provider", "fake", "--corpus", str(ROOT / "corpus" / "routing_smoke"),
                 "--out", str(runs / "dec-fake")]) == 0
    pipeline.SANDBOX_FACTORY = lambda: FakeSandbox()
    try:
        assert main(["usefulness", "run", "--corpus", str(ROOT / "corpus" / "usefulness_v1"), "--reps", "P,M",
                     "--deciders", "none,fake", "--generator", "fake", "--postflight-reps", "M",
                     "--out", str(runs / "use-fake")]) == 0
    finally:
        pipeline.SANDBOX_FACTORY = None
    return tmp_path / "results"


def test_run_kinds_are_recognised(results: Path):
    assert run_kind(results / "runs" / "dec-fake") == "decision"
    assert run_kind(results / "runs" / "use-fake") == "usefulness"


def test_summaries_carry_headline_metrics(results: Path):
    decision = summarize_run(results / "runs" / "dec-fake")
    assert decision["cases"] == 32 and "top1" in decision and decision["synthetic"] is True
    usefulness = summarize_run(results / "runs" / "use-fake")
    assert set(usefulness["arms"]) == {"P+none", "P+fake", "M+none", "M+fake"}
    assert "accuracy" in usefulness["arms"]["M+fake"]


def test_log_appends_jsonl_and_markdown_once_per_run(results: Path):
    log_run(results, results / "runs" / "dec-fake", note="wiring check")
    with pytest.raises(ValueError):
        log_run(results, results / "runs" / "dec-fake", note="again")
    lines = (results / "runs.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1 and json.loads(lines[0])["note"] == "wiring check"
    assert len(json.loads(lines[0])["manifest_sha256"]) == 64
    markdown = (results / "EXPERIMENT_LOG.md").read_text(encoding="utf-8")
    assert "dec-fake" in markdown and "wiring check" in markdown and "SYNTHETIC" in markdown


def test_database_is_rebuilt_from_the_run_folders(results: Path):
    db = results / "rosetta_bench.sqlite"
    counts = build_db(results, db)
    assert counts["runs"] == 2 and counts["decision_cases"] == 32
    assert counts["usefulness_trials"] == 4 * 18
    con = sqlite3.connect(db)
    try:
        arms = {row[0] for row in con.execute("SELECT DISTINCT arm FROM usefulness_trials")}
        assert arms == {"P+none", "P+fake", "M+none", "M+fake"}
        assert con.execute("SELECT COUNT(*) FROM receipts").fetchone()[0] > 0
        assert con.execute("SELECT COUNT(*) FROM corpora").fetchone()[0] >= 2
    finally:
        con.close()  # Windows will not delete an open database file
    again = build_db(results, db)
    assert again == counts


def test_cli_log_and_db(results: Path):
    assert main(["results", "log", "--results", str(results), "--run", str(results / "runs" / "use-fake"), "--note", "n"]) == 0
    assert main(["results", "db", "--results", str(results)]) == 0
    assert (results / "rosetta_bench.sqlite").exists()
