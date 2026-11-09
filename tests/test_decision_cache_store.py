import json
from dataclasses import replace
from pathlib import Path

import pytest

pytest.importorskip("rosetta_core.decision.cache", reason="needs rosetta-core with the decision cache")

from rosetta_core.decision import validate_receipt

from rosetta_bench.cli import main
from rosetta_bench.decision.cache_store import DecisionCache
from rosetta_bench.decision.fake_provider import FakeSystemOne
from rosetta_bench.decision.profiles import PROFILES
from rosetta_bench.decision.shadow import replay_run, run_shadow
from rosetta_bench.decision.transport import FakeTransport

CORPUS = Path(__file__).resolve().parent.parent / "corpus" / "routing_smoke"


def _lines(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()] if path.exists() else []


def _run(tmp_path: Path, name: str, cache: Path, profile=None, transport=None):
    profile = profile or PROFILES["fake"]
    transport = transport or FakeTransport(FakeSystemOne())
    return run_shadow(CORPUS, profile, transport, tmp_path / name, seed=5, cache_path=cache)


def test_store_round_trips_entries_and_counts_hits(tmp_path: Path):
    store = DecisionCache(tmp_path / "c.sqlite")
    store.put({"key": "k" * 64, "expires_at": "2099-01-01T00:00:00+00:00", "created_at": "2026-11-09T00:00:00+00:00", "x": 1})
    assert store.get("k" * 64)["x"] == 1 and store.get("z" * 64) is None
    store.record_hit("k" * 64)
    assert store.stats() == {"entries": 1, "hits": 1}
    store.close()


def test_a_warm_run_makes_no_provider_calls_and_reproduces_the_cold_decisions(tmp_path: Path):
    cache = tmp_path / "cache.sqlite"
    cold = _run(tmp_path, "cold", cache)
    warm_transport = FakeTransport(FakeSystemOne())
    warm = _run(tmp_path, "warm", cache, transport=warm_transport)

    assert warm_transport.requests == []
    assert not (warm / "exchanges.jsonl").exists() or _lines(warm / "exchanges.jsonl") == []
    keep = ("case_id", "outcome", "route", "reason_codes", "signals")
    as_map = lambda run: {d["case_id"]: {k: d[k] for k in keep} for d in _lines(run / "decisions.jsonl")}
    assert as_map(warm) == as_map(cold)

    cold_receipts = {r["case_id"]: r for r in _lines(cold / "receipts.jsonl")}
    for receipt in _lines(warm / "receipts.jsonl"):
        validate_receipt(receipt)
        if receipt["recommendation"]["outcome"] == "DENY":
            assert receipt["cache"]["status"] == "off"
            continue
        assert receipt["cache"]["status"] == "hit"
        assert receipt["cache"]["source_receipt_id"] == cold_receipts[receipt["case_id"]]["receipt_id"]
        assert receipt["usage"]["decision_input_tokens"] == 0
    manifest = json.loads((warm / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["cache"]["hits"] == 31 and manifest["cache"]["misses"] == 0
    assert manifest["cache"]["tokens_avoided"] > 0


def test_cold_run_records_misses_and_fills_the_store(tmp_path: Path):
    cold = _run(tmp_path, "cold", tmp_path / "cache.sqlite")
    manifest = json.loads((cold / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["cache"]["misses"] == 31 and manifest["cache"]["hits"] == 0
    assert DecisionCache(tmp_path / "cache.sqlite").stats()["entries"] == 31


def test_a_different_served_model_never_reuses_entries(tmp_path: Path):
    cache = tmp_path / "cache.sqlite"
    _run(tmp_path, "cold", cache)
    other = replace(PROFILES["fake"], expected_served_model="fake-systemone-2")
    transport = FakeTransport(FakeSystemOne(model="fake-systemone-2"))
    run = _run(tmp_path, "other", cache, profile=other, transport=transport)
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["cache"]["hits"] == 0 and len(transport.requests) == 31


def test_replay_of_a_warm_run_uses_its_cache_snapshot(tmp_path: Path):
    cache = tmp_path / "cache.sqlite"
    _run(tmp_path, "cold", cache)
    warm = _run(tmp_path, "warm", cache)
    cache.unlink()  # replay must not depend on the live cache
    assert replay_run(warm).mismatches == []


def test_cli_accepts_a_cache_path(tmp_path: Path):
    cache = tmp_path / "cache.sqlite"
    for name in ("a", "b"):
        assert main(["decision", "run", "--provider", "fake", "--corpus", str(CORPUS), "--cache", str(cache),
                     "--out", str(tmp_path / name)]) == 0
    assert main(["decision", "report", "--run", str(tmp_path / "b")]) == 0
    report = (tmp_path / "b" / "decision_report.md").read_text(encoding="utf-8")
    assert "Cache: 31 hits, 0 misses" in report
