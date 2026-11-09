import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

import pytest

pytest.importorskip("rosetta_core.decision", reason="decision tests need rosetta-core installed")

from rosetta_core.cpn import parse_packet
from rosetta_core.decision import Primitive, validate_receipt
from rosetta_core.human_doc import extract_fields_comment, extract_notes

from rosetta_bench.catalog import build_db, run_kind, summarize_run
from rosetta_bench.cli import main
from rosetta_bench.decision.eval_corpus import canonical_view, render_corpus
from rosetta_bench.decision.eval_report import compute_metrics
from rosetta_bench.decision.evaluate import load_eval_corpus, noul_verdict, replay_eval, run_eval
from rosetta_bench.decision.masking import Masker
from rosetta_bench.decision.profiles import PROFILES
from rosetta_bench.decision.questions import PASS_ANSWER, QUESTION_SETS, QUESTIONS
from rosetta_bench.decision.transport import FakeTransport, HttpResponse

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "corpus" / "decision_v1"
STATE_TIME = "2026-11-09T12:00:00+00:00"


def _lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _gold() -> dict:
    return {row["item_id"]: row for row in _lines(CORPUS / "gold.jsonl")}


def _items() -> dict:
    return {row["item_id"]: row for row in _lines(CORPUS / "items.jsonl")}


# --- question sets ---------------------------------------------------------------------------------

def test_noul_questions_carry_no_criteria_and_every_set_is_versioned():
    for question in QUESTIONS.values():
        if question.primitive is Primitive.NOUL:
            assert question.criteria is None, question.qid
            assert "Answer yes" in question.instructions and "answer no" in question.instructions.lower()
    for qset in QUESTION_SETS.values():
        assert qset.version == "1.0" and len(qset.content_hash()) == 64
    assert set(PASS_ANSWER) == {q.qid for q in QUESTIONS.values() if q.primitive is Primitive.NOUL}


def test_question_set_hashes_are_pinned():
    """Any wording or option change must come with a version bump and a new pin."""
    pinned = json.loads((CORPUS / "question_sets.json").read_text(encoding="utf-8"))
    assert {name: q.content_hash() for name, q in QUESTION_SETS.items()} == pinned


# --- corpus ------------------------------------------------------------------------------------------

def test_committed_corpus_matches_its_generator():
    for name, text in render_corpus().items():
        assert (CORPUS / name).read_text(encoding="utf-8") == text, f"{name} drifted; regenerate as decision_v2"


def test_every_scored_question_has_20_balanced_items_in_three_languages():
    items, _ = load_eval_corpus(CORPUS)
    golds: dict = defaultdict(Counter)
    languages: dict = defaultdict(set)
    for item in items:
        for qid, gold in item.gold.items():
            golds[qid][gold] += 1
            languages[qid].add(item.language)
    for qid in PASS_ANSWER:
        assert golds[qid][True] + golds[qid][False] >= 20, qid
        assert golds[qid][True] == golds[qid][False], (qid, golds[qid])
        assert languages[qid] == {"en", "zh", "ja"}, qid
    assert golds["intervention_level"] == Counter({None: 20})
    standalone_premise = [i for i in items if i.qset == "premise"]
    assert len(standalone_premise) >= 20


def test_kobayashi_maru_subset_has_paired_no_win_and_near_miss_items():
    items, _ = load_eval_corpus(CORPUS)
    km = [i for i in items if i.subset == "kobayashi_maru"]
    categories = Counter(i.category for i in km)
    assert categories["no_win"] >= 6 and categories["no_win"] == categories["near_miss"]
    for item in km:
        assert set(item.gold) == {"task_feasible", "premise_valid"}
        expected = item.category == "near_miss"
        assert item.gold == {"task_feasible": expected, "premise_valid": expected}
    families = defaultdict(set)
    for item in km:
        families[item.family].add(item.category)
    assert all(kinds == {"no_win", "near_miss"} for kinds in families.values())
    assert {i.language for i in km} == {"en", "zh", "ja"}


def test_intervention_level_is_marked_author_unreviewed():
    for row in _gold().values():
        if "intervention_level" in row["gold"]:
            assert row["gold"]["intervention_level"] is None
            assert row["unreviewed"]["intervention_level"]["review_status"] == "author_unreviewed"


def test_masking_leaves_every_evidence_value_unchanged():
    for item in _items().values():
        assert Masker().mask_value(item["evidence"]) == item["evidence"], item["item_id"]


def test_views_gold_matches_rosetta_core_parsing():
    gold = _gold()
    for item in _items().values():
        if item["qset"] != "views":
            continue
        a, b = item["evidence"]["rosetta.view_a"], item["evidence"]["rosetta.view_b"]
        parse_packet(a)  # view_a is always a valid packet
        assert (canonical_view(a) == canonical_view(b)) == gold[item["item_id"]]["gold"]["views_equivalent"]


def test_notes_pairs_share_fields_and_differ_only_in_notes():
    families = defaultdict(dict)
    for item in _items().values():
        if item["qset"] == "notes":
            families[item["family"]][item["category"]] = item["evidence"]["rosetta.doc"]
    assert len(families) == 10
    for docs in families.values():
        assert extract_fields_comment(docs["faithful"]) == extract_fields_comment(docs["corrupted"])
        assert extract_notes(docs["faithful"]) != extract_notes(docs["corrupted"])


def test_requirements_missing_variant_drops_exactly_one_sentence():
    families = defaultdict(dict)
    for item in _items().values():
        if item["qset"] == "requirements":
            families[item["family"]][item["category"]] = item["evidence"]
    for family in families.values():
        complete, missing = family["complete"]["request.text"], family["missing"]["request.text"]
        assert family["complete"]["requirements.list"] == family["missing"]["requirements.list"]
        assert len(missing) < len(complete)


def test_rosetta_source_premises_reflect_core_behaviour():
    items = _items()
    sync_context = items["prem-en-02-false"]["evidence"]["context.text"]
    assert "raise SyncConflict" in sync_context and "merge" not in sync_context.lower()
    loader_context = items["prem-en-04-true"]["evidence"]["context.text"]
    assert "md_path.read_text" in loader_context


# --- harness ---------------------------------------------------------------------------------------

def _item_id(request: dict) -> str:
    source = next(iter(request["state"]["evidence"].values()))["source"]
    return source.removeprefix("corpus:")


def _oracle(flip: set[tuple[str, str]] = frozenset(), unsure: set[str] = frozenset(), legend: bool = True):
    """Answers from gold (0.9 / 0.1), with chosen (item, qid) answers flipped and chosen items in the band."""
    gold = _gold()

    def respond(request: dict) -> HttpResponse:
        item_id = _item_id(request)
        answers = {}
        for qid, question in request["questions"].items():
            if question["type"] == "score":
                levels = question["criteria"]
                raw = {"type": "score", "score": 1, "confidence": 0.8}
                if legend:
                    raw["legend"] = {str(i + 1): level for i, level in enumerate(levels)}
                answers[qid] = raw
                continue
            truth = gold[item_id]["gold"][qid]
            p = 0.9 if truth else 0.1
            if (item_id, qid) in flip:
                p = 1 - p
            if item_id in unsure:
                p = 0.5
            answers[qid] = {"type": "noul", "noul": p}
        body = {"model": "fake-systemone-1", "answers": answers, "usage": {"input_tokens": 100}}
        return HttpResponse(200, {"content-type": "application/json"}, json.dumps(body).encode("utf-8"))

    return respond


def _run(tmp_path: Path, responder, name="eval", **kwargs) -> Path:
    return run_eval(CORPUS, PROFILES["fake"], FakeTransport(responder), tmp_path / name, seed=7,
                    state_time=STATE_TIME, **kwargs)


def test_placeholder_thresholds():
    assert noul_verdict(0.7) == "yes" and noul_verdict(0.3) == "no" and noul_verdict(0.5) == "abstain"


def test_oracle_run_scores_perfectly_and_writes_valid_receipts(tmp_path: Path):
    transport = FakeTransport(_oracle())
    out = run_eval(CORPUS, PROFILES["fake"], transport, tmp_path / "eval", seed=7, state_time=STATE_TIME)
    items, _ = load_eval_corpus(CORPUS)
    decisions, receipts = _lines(out / "decisions.jsonl"), _lines(out / "receipts.jsonl")
    assert len(decisions) == len(receipts) == len(items)
    assert len(transport.requests) == len(items)  # one call per item: no semantic retries
    for receipt in receipts:
        validate_receipt(receipt)
        assert receipt["mode"] == "shadow" and receipt["executed_route"] is None
        assert receipt["retries"]["semantic"] == 0
    metrics = compute_metrics(out)
    for qid, entry in metrics["questions"].items():
        assert entry["all"]["accuracy"] == 1.0, qid
        assert entry["all"]["false_pass"] == 0 and entry["all"]["abstain"] == 0
        assert entry["all"]["brier"] == pytest.approx(0.01)
    unreviewed = metrics["unreviewed"]["intervention_level"]
    assert unreviewed["answered"] == 20 and unreviewed["levels"] == {"none": 20}
    assert unreviewed["agrees_with_author_estimate"] == 10  # the 10 complete requests


def test_false_passes_over_refusals_and_kobayashi_maru_subset(tmp_path: Path):
    items, _ = load_eval_corpus(CORPUS)
    no_win = [i.item_id for i in items if i.category == "no_win"]
    near = [i.item_id for i in items if i.category == "near_miss"]
    flip = {(no_win[0], "task_feasible"), (no_win[1], "premise_valid"), (near[0], "task_feasible"),
            ("mean-en-01", "meaning_changed")}
    out = _run(tmp_path, _oracle(flip=flip, unsure={"notes-en-01-corrupted"}))
    m = compute_metrics(out)
    km = m["subsets"]["kobayashi_maru"]
    assert km["task_feasible"]["inside"]["false_pass"] == 1  # false 'feasible' on a no-win item
    assert km["task_feasible"]["inside"]["over_refusal"] == 1  # false 'infeasible' on a near-miss
    assert km["premise_valid"]["inside"]["false_pass"] == 1
    assert km["task_feasible"]["outside"]["n"] == 10 and km["task_feasible"]["outside"]["accuracy"] == 1.0
    tf = m["questions"]["task_feasible"]["all"]
    assert tf["n"] == 22 and tf["correct"] == 20
    # meaning_changed passes on "no": calling a negated passage unchanged is a false pass
    assert m["questions"]["meaning_changed"]["all"]["false_pass"] == 1
    notes = m["questions"]["notes_consistent"]["all"]
    assert notes["abstain"] == 1 and notes["correct"] == 19 and notes["decided_accuracy"] == 1.0
    assert notes["confusion"]["gold_no"]["abstain"] == 1
    assert m["questions"]["notes_consistent"]["by_language"]["en"]["abstain"] == 1


def test_provider_errors_are_typed_and_never_verdicts(tmp_path: Path):
    out = _run(tmp_path, lambda request: HttpResponse(400, {}, b'{"error":{"type":"invalid_request"}}'))
    decisions = _lines(out / "decisions.jsonl")
    assert {d["outcome"] for d in decisions} == {"FALLBACK"}
    assert all(d["provider_error"]["kind"] == "INVALID_REQUEST" for d in decisions)
    m = compute_metrics(out)
    for entry in m["questions"].values():
        assert entry["all"]["correct"] == 0 and entry["all"]["false_pass"] == 0
        assert entry["all"]["errors"] == entry["all"]["n"]


def test_score_without_legend_stays_unmapped(tmp_path: Path):
    out = _run(tmp_path, _oracle(legend=False))
    m = compute_metrics(out)
    assert m["unreviewed"]["intervention_level"]["answered"] == 0
    assert m["unreviewed"]["intervention_level"]["errors"] == {"MISSING": 20}
    assert m["questions"]["requirements_sufficient"]["all"]["accuracy"] == 1.0
    assert m["raw_score_shapes"]["field_sets"] == {"confidence,score,type": 20}


def test_replay_reproduces_every_verdict_offline(tmp_path: Path):
    out = _run(tmp_path, _oracle(flip={("mean-en-01", "meaning_changed")}, unsure={"views-en-01-equal-reorder"}))
    report = replay_eval(out)
    assert report.items == 142 and report.mismatches == []


def test_replay_detects_a_changed_recording(tmp_path: Path):
    out = _run(tmp_path, _oracle())
    path = out / "decisions.jsonl"
    decisions = _lines(path)
    decisions[0]["outcome"] = "ABSTAIN"
    path.write_text("".join(json.dumps(d, ensure_ascii=False) + "\n" for d in decisions), encoding="utf-8")
    assert replay_eval(out).mismatches == [decisions[0]["item_id"]]


# --- CLI and catalog ---------------------------------------------------------------------------------

def test_cli_eval_replay_report_and_budget(tmp_path: Path):
    out = tmp_path / "cli-eval"
    assert main(["decision", "eval", "--corpus", str(CORPUS), "--provider", "fake", "--out", str(out)]) == 0
    assert main(["decision", "replay", "--run", str(out)]) == 0
    assert main(["decision", "report", "--run", str(out)]) == 0
    report = (out / "eval_report.md").read_text(encoding="utf-8")
    assert "SYNTHETIC" in report and "kobayashi_maru" in report and "intervention_level" in report
    assert json.loads((out / "metrics.json").read_text(encoding="utf-8"))["items"] == 142
    small = tmp_path / "budget"
    assert main(["decision", "eval", "--corpus", str(CORPUS), "--provider", "fake", "--out", str(small), "--max-calls", "3"]) == 0
    manifest = json.loads((small / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["stopped_early"] and len(_lines(small / "decisions.jsonl")) == 3
    assert main(["decision", "replay", "--run", str(small)]) == 0
    one = tmp_path / "one"
    assert main(["decision", "eval", "--corpus", str(CORPUS), "--provider", "fake", "--out", str(one),
                 "--items", "req-en-01-complete"]) == 0
    assert [d["item_id"] for d in _lines(one / "decisions.jsonl")] == ["req-en-01-complete"]


def test_cli_refuses_live_providers_without_confirmation(tmp_path: Path):
    assert main(["decision", "eval", "--corpus", str(CORPUS), "--provider", "clef-ollama", "--out", str(tmp_path / "x")]) == 2
    assert main(["decision", "eval", "--corpus", str(CORPUS), "--provider", "clef-ollama", "--live", "--out", str(tmp_path / "y")]) == 2
    assert not (tmp_path / "x").exists() and not (tmp_path / "y").exists()


def test_catalog_knows_eval_runs(tmp_path: Path):
    results = tmp_path / "results"
    out = _run(results / "runs", _oracle(flip={("mean-en-01", "meaning_changed")}), name="eval-fake")
    assert run_kind(out) == "decision_eval"
    summary = summarize_run(out)
    assert summary["items"] == 142 and summary["questions"]["meaning_changed"]["false_pass"] == 1
    db = results / "rosetta_bench.sqlite"
    counts = build_db(results, db)
    assert counts["eval_answers"] == 142 + 12 + 20  # one row per question asked
    con = sqlite3.connect(db)
    try:
        row = con.execute("SELECT n, correct, false_pass FROM eval_metrics WHERE qid='task_feasible' AND scope='subset'").fetchone()
        assert row == (12, 12, 0)
        assert con.execute("SELECT COUNT(*) FROM receipts").fetchone()[0] == 142
    finally:
        con.close()
