import json
from pathlib import Path

import pytest

pytest.importorskip("rosetta_core.decision", reason="needs rosetta-core")

from rosetta_bench.cli import main
from rosetta_bench.decision.battery import COMPACT_VERSION, intake_battery, intake_battery_compact
from rosetta_bench.decision.fake_provider import FakeSystemOne
from rosetta_bench.decision.profiles import PROFILES
from rosetta_bench.decision.shadow import load_routing_corpus, replay_run, run_shadow
from rosetta_bench.decision.transport import FakeTransport

CORPUS = Path(__file__).resolve().parent.parent / "corpus" / "routing_smoke"
ROUTES = load_routing_corpus(CORPUS)[0]


def _lines(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def test_compact_questions_point_at_the_route_list_instead_of_repeating_it():
    full, compact = intake_battery(ROUTES), intake_battery_compact(ROUTES)
    assert compact.version == COMPACT_VERSION and compact.content_hash() != full.content_hash()
    options = compact.get("workflow_route").criteria
    assert list(options) == list(full.get("workflow_route").criteria)  # same options, same order
    assert all(text == f"as described in `routes.{rid}`" for rid, text in options.items())
    assert sum(len(q.instructions) for q in compact.questions) < 0.7 * sum(len(q.instructions) for q in full.questions)


def test_compact_requests_send_the_route_list_once_and_are_smaller(tmp_path: Path):
    sizes = {}
    for name, compact in (("full", False), ("compact", True)):
        transport = FakeTransport(FakeSystemOne())
        run_shadow(CORPUS, PROFILES["fake"], transport, tmp_path / name, seed=5, compact=compact)
        bodies = [r["raw"] for r in transport.requests]
        sizes[name] = sum(len(b) for b in bodies) / len(bodies)
        assert all("routes" in r["body"]["state"] for r in transport.requests)  # every question can still see the routes
    assert sizes["compact"] < 0.8 * sizes["full"]


def test_compact_run_records_its_format_and_replays_exactly(tmp_path: Path):
    out = run_shadow(CORPUS, PROFILES["fake"], FakeTransport(FakeSystemOne()), tmp_path / "c", seed=5, compact=True)
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["state_format"] == "compact" and manifest["question_set"]["version"] == COMPACT_VERSION
    assert replay_run(out).mismatches == []


def test_cli_compact_flag(tmp_path: Path):
    out = tmp_path / "cli"
    assert main(["decision", "run", "--provider", "fake", "--corpus", str(CORPUS), "--compact", "--out", str(out)]) == 0
    assert json.loads((out / "manifest.json").read_text(encoding="utf-8"))["state_format"] == "compact"
