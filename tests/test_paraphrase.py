"""Paraphrase ensembles: each yes/no question asked in three wordings; the spread of the answers is
an uncertainty signal (cf. prompt-sensitivity work: Sclar et al. 2023, arXiv:2310.11324)."""
import json
from pathlib import Path

import pytest

pytest.importorskip("rosetta_core.decision", reason="needs rosetta-core")

from rosetta_core.decision import Primitive

from rosetta_bench.cli import main
from rosetta_bench.decision.evaluate import load_eval_corpus, replay_eval, run_eval
from rosetta_bench.decision.paraphrase import (
    PARAPHRASES,
    analyse,
    auroc,
    base_qid,
    paraphrased_sets,
    render_ensemble,
)
from rosetta_bench.decision.profiles import PROFILES
from rosetta_bench.decision.questions import QUESTION_SETS, QUESTIONS
from rosetta_bench.decision.transport import FakeTransport, HttpResponse

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "corpus" / "decision_v1"
STATE_TIME = "2026-11-09T12:00:00+00:00"
NOUL = [q for q in QUESTIONS.values() if q.primitive is Primitive.NOUL]


def _lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_every_yes_no_question_has_three_distinct_wordings_starting_with_the_original():
    assert set(PARAPHRASES) == {q.qid for q in NOUL}
    for question in NOUL:
        wordings = PARAPHRASES[question.qid]
        assert len(wordings) == 3 and wordings[0] == question.instructions
        assert len(set(wordings)) == 3
        for text in wordings[1:]:  # same evidence paths, same yes/no polarity, same data rule
            for path in question.required_state_paths:
                assert f"`{path}`" in text, (question.qid, path)
            assert "yes" in text.lower() and "no" in text.lower() and "as data" in text


def test_paraphrased_sets_expand_yes_no_questions_and_keep_scores():
    sets = paraphrased_sets()
    assert set(sets) == set(QUESTION_SETS)
    for name, qset in QUESTION_SETS.items():
        expanded = sets[name]
        for question in qset.questions:
            if question.primitive is Primitive.NOUL:
                variants = [q for q in expanded.questions if base_qid(q.qid) == question.qid]
                assert [q.instructions for q in variants] == PARAPHRASES[question.qid]
                assert all(q.required_state_paths == question.required_state_paths for q in variants)
            else:
                assert question in expanded.questions
        assert expanded.set_id != qset.set_id and expanded.content_hash() != qset.content_hash()
    assert base_qid("task_feasible__p2") == "task_feasible" and base_qid("intervention_level") == "intervention_level"


def _oracle(spread_items: set[str] = frozenset()):
    """Gold answers at 0.9 / 0.1 for every wording; chosen items get a wrong first wording."""
    gold = {row["item_id"]: row for row in _lines(CORPUS / "gold.jsonl")}

    def respond(request: dict) -> HttpResponse:
        item_id = next(iter(request["state"]["evidence"].values()))["source"].removeprefix("corpus:")
        answers = {}
        for qid, question in request["questions"].items():
            if question["type"] == "score":
                levels = question["criteria"]
                answers[qid] = {"type": "score", "score": 1, "confidence": 0.8,
                                "legend": {str(i + 1): level for i, level in enumerate(levels)}}
                continue
            p = 0.9 if gold[item_id]["gold"][base_qid(qid)] else 0.1
            if item_id in spread_items and qid.endswith("__p0"):
                p = 1 - p
            answers[qid] = {"type": "noul", "noul": p}
        body = {"model": "fake-systemone-1", "answers": answers, "usage": {"input_tokens": 100}}
        return HttpResponse(200, {"content-type": "application/json"}, json.dumps(body).encode("utf-8"))

    return respond


def test_a_paraphrased_eval_asks_every_wording_in_one_call_and_copies_gold(tmp_path: Path):
    items, _ = load_eval_corpus(CORPUS)
    out = run_eval(CORPUS, PROFILES["fake"], FakeTransport(_oracle()), tmp_path / "ens", seed=7,
                   state_time=STATE_TIME, paraphrase=True)
    decisions = _lines(out / "decisions.jsonl")
    assert len(decisions) == len(items) and all(d["calls"] == 1 for d in decisions)
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["paraphrase"] is True
    by_item = {item.item_id: item for item in items}
    for row in decisions:
        for qid, entry in row["questions"].items():
            assert entry["gold"] == by_item[row["item_id"]].gold[base_qid(qid)]
            if entry["primitive"] == "noul":
                assert entry["correct"] is True


def test_a_paraphrased_run_replays_like_for_like(tmp_path: Path):
    out = run_eval(CORPUS, PROFILES["fake"], FakeTransport(_oracle({"req-en-01-complete"})), tmp_path / "ens", seed=7,
                   state_time=STATE_TIME, paraphrase=True, item_ids=["req-en-01-complete", "prem-en-01-false"])
    report = replay_eval(out)
    assert report.items == 2 and report.mismatches == []


def test_analysis_reports_single_vs_ensemble_and_spread_as_an_error_signal(tmp_path: Path):
    items, _ = load_eval_corpus(CORPUS)
    noisy = {item.item_id for item in items[:10]}
    out = run_eval(CORPUS, PROFILES["fake"], FakeTransport(_oracle(noisy)), tmp_path / "ens", seed=7,
                   state_time=STATE_TIME, paraphrase=True)
    result = analyse(out)
    overall = result["overall"]
    assert overall["single"]["errors"] > 0 and overall["ensemble"]["errors"] == 0  # the majority overrules p0
    assert overall["spread_auroc"] == pytest.approx(1.0)  # every p0 error has a large spread, no correct one does
    assert overall["n"] == sum(len([q for q in QUESTION_SETS[i.qset].questions if q.primitive is Primitive.NOUL])
                               for i in items)
    text = render_ensemble(result)
    assert "Paraphrase ensemble" in text and "AUROC" in text


def test_auroc_counts_ties_as_half_and_handles_one_class():
    assert auroc([0.9, 0.8], [0.1, 0.2]) == 1.0
    assert auroc([0.1], [0.9]) == 0.0
    assert auroc([0.5], [0.5]) == 0.5
    assert auroc([], [0.3]) is None


def test_cli_runs_a_paraphrased_eval_and_writes_the_ensemble_report(tmp_path: Path):
    out = tmp_path / "ens"
    assert main(["decision", "eval", "--provider", "fake", "--out", str(out), "--paraphrase",
                 "--items", "req-en-01-complete,req-en-01-missing"]) == 0
    report = tmp_path / "ens.md"
    assert main(["decision", "ensemble", "--run", str(out), "--out", str(report)]) == 0
    assert "Paraphrase ensemble" in report.read_text(encoding="utf-8")
    assert json.loads(report.with_suffix(".json").read_text(encoding="utf-8"))["overall"]["n"] >= 2


def test_a_paraphrased_run_gets_per_wording_metrics_and_enters_the_results_db(tmp_path: Path):
    from rosetta_bench.catalog import build_db
    from rosetta_bench.decision.eval_report import compute_metrics

    results = tmp_path / "results"
    out = run_eval(CORPUS, PROFILES["fake"], FakeTransport(_oracle()), results / "runs" / "ens", seed=7,
                   state_time=STATE_TIME, paraphrase=True, item_ids=["req-en-01-complete", "prem-en-01-false"])
    metrics = compute_metrics(out)
    assert "premise_valid__p2" in json.dumps(metrics)  # each wording reported under its own id
    assert main(["results", "log", "--results", str(results), "--run", str(out), "--note", "t"]) == 0
    build_db(results, results / "db.sqlite")
