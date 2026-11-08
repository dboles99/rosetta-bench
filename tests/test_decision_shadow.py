import json
from pathlib import Path

import pytest

pytest.importorskip("rosetta_core.decision", reason="decision tests need rosetta-core installed")

from rosetta_core.decision import validate_receipt

from rosetta_bench.cli import main
from rosetta_bench.decision.shadow import load_routing_corpus, replay_run
from rosetta_bench.decision.probe import run_probe
from rosetta_bench.decision.profiles import PROFILES
from rosetta_bench.decision.transport import FakeTransport, HttpResponse

CORPUS = Path(__file__).resolve().parent.parent / "corpus" / "routing_smoke"


def _lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _run(tmp_path: Path, *extra) -> Path:
    out = tmp_path / "decision-run"
    code = main(["decision", "run", "--corpus", str(CORPUS), "--provider", "fake", "--out", str(out), "--seed", "11", *extra])
    assert code == 0
    return out


def test_routing_corpus_is_well_formed():
    routes, cases, digest = load_routing_corpus(CORPUS)
    route_ids = {route["id"] for route in routes}
    assert len(cases) >= 30
    assert len({case.case_id for case in cases}) == len(cases)
    for case in cases:
        assert set(case.eligible_routes) <= route_ids
        assert (case.label_route is None) == (not case.label_fits), case.case_id
        assert case.label_route is None or case.label_route in route_ids
    categories = {case.category for case in cases}
    assert {"obvious", "ambiguous", "no_fit", "adversarial", "gate"} <= categories
    assert len(digest) == 64


def test_shadow_run_writes_valid_receipts_and_executes_the_baseline_route(tmp_path: Path):
    out = _run(tmp_path)
    receipts = _lines(out / "receipts.jsonl")
    decisions = _lines(out / "decisions.jsonl")
    _, cases, _ = load_routing_corpus(CORPUS)
    assert len(receipts) == len(decisions) == len(cases)
    baseline = {case.case_id: case.baseline_route for case in cases}
    for receipt in receipts:
        validate_receipt(receipt)
        assert receipt["mode"] == "shadow"
        assert receipt["executed_route"] == baseline[receipt["case_id"]]
        assert receipt["cost"]["basis"] == "free_local"
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["synthetic"] is True
    assert manifest["live"] is False
    assert manifest["policy"]["calibrated"] is False


def test_gate_denied_cases_never_reach_the_provider(tmp_path: Path):
    out = _run(tmp_path)
    denied = [d for d in _lines(out / "decisions.jsonl") if d["outcome"] == "DENY"]
    assert denied, "corpus needs at least one gate case"
    called = {e["case_id"] for e in _lines(out / "exchanges.jsonl")}
    assert not called & {d["case_id"] for d in denied}


def test_masked_values_never_leave_the_run_in_clear(tmp_path: Path):
    out = _run(tmp_path)
    for name in ("exchanges.jsonl", "receipts.jsonl", "decisions.jsonl"):
        assert "dev-team@example.com" not in (out / name).read_text(encoding="utf-8")
    assert "<email1>" in (out / "exchanges.jsonl").read_text(encoding="utf-8")


def test_replay_reproduces_every_recommendation(tmp_path: Path):
    out = _run(tmp_path)
    report = replay_run(out)
    assert report.cases == len(_lines(out / "decisions.jsonl"))
    assert report.mismatches == []
    assert main(["decision", "replay", "--run", str(out)]) == 0


def test_replay_detects_a_changed_provider_reply(tmp_path: Path):
    out = _run(tmp_path)
    exchanges = _lines(out / "exchanges.jsonl")
    first = exchanges[0]
    reply = json.loads(first["response_body"])
    reply["answers"]["route_fits"]["noul"] = 0.0 if reply["answers"]["route_fits"]["noul"] > 0.5 else 1.0
    first["response_body"] = json.dumps(reply)
    (out / "exchanges.jsonl").write_text("".join(json.dumps(e) + "\n" for e in exchanges), encoding="utf-8")
    assert replay_run(out).mismatches == [first["case_id"]]
    assert main(["decision", "replay", "--run", str(out)]) == 1


def test_report_is_labelled_synthetic_and_counts_outcomes(tmp_path: Path):
    out = _run(tmp_path)
    assert main(["decision", "report", "--run", str(out)]) == 0
    report = (out / "decision_report.md").read_text(encoding="utf-8")
    assert "SYNTHETIC" in report
    assert "Brier" in report
    assert "False accepts on no-fit cases" in report


def test_live_providers_need_the_live_flag(tmp_path: Path, capsys):
    code = main(["decision", "run", "--corpus", str(CORPUS), "--provider", "jevmodel", "--out", str(tmp_path / "x")])
    assert code == 2
    assert "--live" in capsys.readouterr().err
    assert not (tmp_path / "x").exists()


def test_live_run_without_a_key_names_the_variable_and_stops(tmp_path: Path, capsys, monkeypatch):
    monkeypatch.delenv("JEVMODEL_API_KEY", raising=False)
    code = main(["decision", "run", "--corpus", str(CORPUS), "--provider", "jevmodel", "--live", "--out", str(tmp_path / "x")])
    assert code == 2
    assert "JEVMODEL_API_KEY" in capsys.readouterr().err
    assert not (tmp_path / "x").exists()


def test_call_budget_stops_the_run_early(tmp_path: Path):
    out = _run(tmp_path, "--max-calls", "3")
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["stopped_early"].startswith("call budget")
    assert len(_lines(out / "exchanges.jsonl")) == 3


class _VersionedFake:
    """Fake server that answers like FakeSystemOne but reports a versioned model."""

    def __init__(self, served: str):
        from rosetta_bench.decision.fake_provider import FakeSystemOne

        self._inner = FakeSystemOne()
        self._served = served

    def __call__(self, request):
        reply = self._inner(request)
        body = json.loads(reply.body)
        body["model"] = self._served
        return HttpResponse(200, reply.headers, json.dumps(body).encode())


def _versioned_run(tmp_path: Path, served: str, expected: str, base: str = "fake") -> list[dict]:
    from dataclasses import replace

    from rosetta_bench.decision.shadow import run_shadow

    profile = replace(PROFILES[base], expected_served_model=expected)
    out = run_shadow(CORPUS, profile, FakeTransport(_VersionedFake(served)), tmp_path / served, seed=3)
    return _lines(out / "decisions.jsonl")


def test_policy_is_pinned_to_the_expected_served_revision_not_the_requested_alias(tmp_path: Path):
    decisions = _versioned_run(tmp_path, served="fake-1.14.0", expected="fake-1.14.0")
    assert not any("CALIBRATION_STALE" in d["reason_codes"] for d in decisions)
    receipts = _lines(tmp_path / "fake-1.14.0" / "receipts.jsonl")
    called = [r for r in receipts if r["provider"]["served_model"]]
    assert called and all(r["provider"]["revision_known"] for r in called)


def test_a_different_served_revision_falls_back_on_every_called_case(tmp_path: Path):
    decisions = _versioned_run(tmp_path, served="fake-1.15.0", expected="fake-1.14.0")
    called = [d for d in decisions if d["served_model"]]
    assert called and all(d["outcome"] == "FALLBACK" and d["reason_codes"] == ["CALIBRATION_STALE"] for d in called)


def test_jevmodel_profile_expects_the_revision_seen_by_the_probe():
    assert PROFILES["jevmodel"].default_model == "jev-latest"
    assert PROFILES["jevmodel"].expected_served_model == "jev-1.14.0"


def test_clef_profile_expects_its_unversioned_served_name(tmp_path: Path):
    assert PROFILES["clef-ollama"].expected_served_model == "clef"
    # clef-ollama's own profile (pins_versions False), served through the offline fake transport
    decisions = _versioned_run(tmp_path, served="clef", expected="clef", base="clef-ollama")
    assert not any("CALIBRATION_STALE" in d["reason_codes"] for d in decisions)
    receipts = _lines(tmp_path / "clef" / "receipts.jsonl")
    called = [r for r in receipts if r["provider"]["served_model"]]
    assert called and not any(r["provider"]["revision_known"] for r in called)


def test_probe_records_capabilities_without_the_key(tmp_path: Path):
    key = "probe-key-" + "z" * 20
    reply = {
        "model": "jev-latest",
        "answers": {
            "route_fits": {"type": "noul", "noul": 0.9},
            "workflow_route": {"type": "choice", "choice": "code_change", "probabilities": {"code_change": 0.9}, "confidence": 0.8},
        },
        "usage": {"input_tokens": 200},
    }
    transport = FakeTransport([HttpResponse(200, {"x-tokens-remaining": "99800"}, json.dumps(reply).encode())])
    probe = run_probe(PROFILES["jevmodel"], transport, key, CORPUS, tmp_path / "probe")
    assert probe["served_model"] == "jev-latest"
    assert probe["calls"] == 1
    assert probe["tokens_remaining"] == "99800"
    assert probe["fields"]["workflow_route"] == ["choice", "confidence", "probabilities", "type"]
    written = (tmp_path / "probe" / "probe.json").read_text(encoding="utf-8")
    assert key not in written
    assert len(transport.requests) == 1
