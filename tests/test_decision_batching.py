import json
import math
from dataclasses import replace
from pathlib import Path

import pytest

pytest.importorskip("rosetta_core.decision", reason="needs rosetta-core")

from rosetta_core.decision import validate_receipt

from rosetta_bench.cli import main
from rosetta_bench.decision.battery import batched_call_battery, intake_slot_battery
from rosetta_bench.decision.fake_provider import FakeSystemOne
from rosetta_bench.decision.profiles import PROFILES
from rosetta_bench.decision.shadow import load_routing_corpus, replay_run, run_shadow
from rosetta_bench.decision.transport import FakeTransport

CORPUS = Path(__file__).resolve().parent.parent / "corpus" / "routing_smoke"
ROUTES = load_routing_corpus(CORPUS)[0]


def _lines(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()] if path.exists() else []


def test_slot_questions_point_at_their_own_item_and_keep_plain_ids():
    slot = intake_slot_battery(ROUTES, "r2")
    assert slot.qids == ("route_fits", "workflow_route")
    assert all("items.r2" in q.instructions and "independently" in q.instructions for q in slot.questions)
    call = batched_call_battery(ROUTES, ["r1", "r2"])
    assert call.qids == ("route_fits_r1", "workflow_route_r1", "route_fits_r2", "workflow_route_r2")
    assert call.version != intake_slot_battery(ROUTES, "r1").version or call.set_id != "intake"


def _run(tmp_path, name, batch_size, transport=None, profile=None, **kwargs):
    transport = transport or FakeTransport(FakeSystemOne())
    return run_shadow(CORPUS, profile or PROFILES["fake"], transport, tmp_path / name, seed=5, batch_size=batch_size, **kwargs), transport


def test_batching_cuts_calls_and_keeps_the_fake_decisions(tmp_path: Path):
    single, single_transport = _run(tmp_path, "single", 1)
    batched, batched_transport = _run(tmp_path, "batched", 4)
    assert len(single_transport.requests) == 31
    assert len(batched_transport.requests) == math.ceil(31 / 4)
    keep = ("outcome", "route")
    as_map = lambda run: {d["case_id"]: tuple(d[k] for k in keep) for d in _lines(run / "decisions.jsonl")}
    assert as_map(batched) == as_map(single)


def test_token_shares_add_up_to_the_call_and_receipts_validate(tmp_path: Path):
    batched, _ = _run(tmp_path, "batched", 4)
    decisions = _lines(batched / "decisions.jsonl")
    by_batch = {}
    for d in decisions:
        if d.get("batch"):
            by_batch.setdefault(d["batch"]["batch_id"], []).append(d)
    assert by_batch and all(sum(x["input_tokens"] for x in items) == items[0]["batch"]["call_input_tokens"] for items in by_batch.values())
    assert sum(d["calls"] for d in decisions) == len(by_batch)
    for receipt in _lines(batched / "receipts.jsonl"):
        validate_receipt(receipt)
    manifest = json.loads((batched / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["batching"]["size"] == 4 and len(manifest["batching"]["slot_question_sets"]) == 4


def test_a_batch_beyond_the_provider_question_cap_is_refused_before_any_call(tmp_path: Path):
    profile = replace(PROFILES["jevmodel"], expected_served_model="fake-systemone-1")
    transport = FakeTransport(FakeSystemOne())
    with pytest.raises(ValueError):
        _run(tmp_path, "too-big", 5, transport=transport, profile=profile, api_key="dummy-key-for-test")
    assert transport.requests == []


def test_batching_and_the_cache_are_not_combined_yet(tmp_path: Path):
    with pytest.raises(ValueError):
        _run(tmp_path, "both", 4, cache_path=tmp_path / "c.sqlite")


def test_replay_of_a_batched_run_is_exact(tmp_path: Path):
    batched, _ = _run(tmp_path, "batched", 3)
    assert replay_run(batched).mismatches == []


def test_cli_batch_size(tmp_path: Path):
    out = tmp_path / "cli"
    assert main(["decision", "run", "--provider", "fake", "--corpus", str(CORPUS), "--batch-size", "4", "--out", str(out)]) == 0
    assert main(["decision", "report", "--run", str(out)]) == 0
    assert "Batching: 4 requests per call" in (out / "decision_report.md").read_text(encoding="utf-8")
