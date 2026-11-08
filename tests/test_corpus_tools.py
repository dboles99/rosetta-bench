import json
from pathlib import Path

import openpyxl
import pytest

pytest.importorskip("rosetta_core.decision", reason="decision tests need rosetta-core installed")

from rosetta_bench.corpus_tools import (
    LabelImportError,
    assign_splits,
    export_labelling_sheet,
    import_labels,
    load_splits,
    write_splits,
)
from rosetta_bench.decision.shadow import MissingLabels, load_routing_corpus

ROUTES = {"version": "1.0", "routes": [
    {"id": "code_change", "description": "Change code"},
    {"id": "docs_edit", "description": "Edit docs"},
    {"id": "clarify", "description": "Ask for details"},
]}


def _corpus(tmp_path: Path, families: int = 6, variants: int = 3) -> Path:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "routes.json").write_text(json.dumps(ROUTES), encoding="utf-8")
    kinds = ["code", "docs", "no_fit"]
    cases, author = [], []
    for f in range(families):
        kind = kinds[f % 3]
        for v in range(variants):
            cid = f"f{f:02d}v{v}"
            cases.append({"case_id": cid, "family": f"f{f:02d}", "family_kind": kind, "language": "en",
                          "request_text": f"request text for case {cid}"})
            route = {"code": "code_change", "docs": "docs_edit", "no_fit": None}[kind]
            author.append({"case_id": cid, "label_fits": route is not None, "label_route": route})
    (corpus / "cases.jsonl").write_text("".join(json.dumps(c) + "\n" for c in cases), encoding="utf-8")
    (corpus / "author_labels.jsonl").write_text("".join(json.dumps(a) + "\n" for a in author), encoding="utf-8")
    return corpus


def _fill_sheet(path: Path, answer) -> None:
    workbook = openpyxl.load_workbook(path)
    sheet = workbook["label"]
    for row in sheet.iter_rows(min_row=2):
        row[2].value = answer(row[0].value)
    workbook.save(path)


def test_unlabelled_corpus_refuses_to_load_for_scoring(tmp_path: Path):
    with pytest.raises(MissingLabels):
        load_routing_corpus(_corpus(tmp_path))


def test_splits_keep_every_family_on_one_side_and_cover_each_kind(tmp_path: Path):
    corpus = _corpus(tmp_path, families=12)
    splits = assign_splits(corpus, seed=5, calibration_fraction=0.4)
    assert set(splits.values()) == {"calibration", "held_out"}
    cases = [json.loads(l) for l in (corpus / "cases.jsonl").read_text(encoding="utf-8").splitlines()]
    kinds = {}
    for case in cases:
        kinds.setdefault(case["family_kind"], set()).add(splits[case["family"]])
    assert all(sides == {"calibration", "held_out"} for sides in kinds.values())


def test_splits_are_reproducible_and_written_with_a_hash(tmp_path: Path):
    corpus = _corpus(tmp_path, families=12)
    assert assign_splits(corpus, seed=5) == assign_splits(corpus, seed=5)
    write_splits(corpus, seed=5)
    data = load_splits(corpus)
    assert len(data["hash"]) == 64
    with pytest.raises(FileExistsError):
        write_splits(corpus, seed=6)


def test_labelling_sheet_is_blind_and_offers_a_fixed_choice(tmp_path: Path):
    corpus = _corpus(tmp_path)
    sheet = tmp_path / "to_label.xlsx"
    export_labelling_sheet(corpus, sheet, seed=1)
    workbook = openpyxl.load_workbook(sheet)
    label = workbook["label"]
    header = [cell.value for cell in label[1]]
    assert header == ["case_id", "request_text", "route", "unsure", "notes"]
    text = json.dumps([[c.value for c in row] for row in label.iter_rows()])
    assert "family" not in text and "no_fit" not in text and "label" not in text.replace('"label"', "")
    validations = label.data_validations.dataValidation
    assert any("code_change" in (v.formula1 or "") and "none" in (v.formula1 or "") for v in validations)
    assert "routes" in workbook.sheetnames


def test_imported_labels_are_validated_written_and_frozen(tmp_path: Path):
    corpus = _corpus(tmp_path)
    sheet = tmp_path / "to_label.xlsx"
    export_labelling_sheet(corpus, sheet, seed=1)
    author = {json.loads(l)["case_id"]: json.loads(l) for l in (corpus / "author_labels.jsonl").read_text(encoding="utf-8").splitlines()}
    _fill_sheet(sheet, lambda cid: author[cid]["label_route"] or "none")

    summary = import_labels(corpus, sheet, labeller="dan")
    assert summary["cases"] == 18
    assert summary["agreement_with_author"] == 1.0
    routes, cases, _ = load_routing_corpus(corpus)
    assert all(case.label_source == "dan" for case in cases)
    assert {case.label_route for case in cases} == {"code_change", "docs_edit", None}
    with pytest.raises(FileExistsError):
        import_labels(corpus, sheet, labeller="dan")


def test_cli_split_sheet_import_and_a_split_restricted_run(tmp_path: Path):
    from rosetta_bench.cli import main
    from rosetta_bench.decision.shadow import replay_run

    corpus = _corpus(tmp_path, families=12)
    sheet = tmp_path / "sheet.xlsx"
    assert main(["corpus", "split", "--corpus", str(corpus), "--seed", "4"]) == 0
    assert main(["corpus", "sheet", "--corpus", str(corpus), "--out", str(sheet), "--seed", "4"]) == 0
    author = {json.loads(l)["case_id"]: json.loads(l) for l in (corpus / "author_labels.jsonl").read_text(encoding="utf-8").splitlines()}
    _fill_sheet(sheet, lambda cid: author[cid]["label_route"] or "none")
    assert main(["corpus", "import-labels", "--corpus", str(corpus), "--sheet", str(sheet), "--labeller", "dan"]) == 0

    out = tmp_path / "run"
    assert main(["decision", "run", "--corpus", str(corpus), "--provider", "fake", "--out", str(out), "--split", "calibration"]) == 0
    splits = load_splits(corpus)["families"]
    decided = [json.loads(l) for l in (out / "decisions.jsonl").read_text(encoding="utf-8").splitlines()]
    families = {d["case_id"][:3] for d in decided}
    assert decided and all(splits[f] == "calibration" for f in families)
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["split"] == "calibration" and len(manifest["splits_hash"]) == 64
    assert replay_run(out).mismatches == []


def test_import_rejects_blank_or_unknown_routes(tmp_path: Path):
    corpus = _corpus(tmp_path)
    sheet = tmp_path / "to_label.xlsx"
    export_labelling_sheet(corpus, sheet, seed=1)
    _fill_sheet(sheet, lambda cid: "deploy" if cid.endswith("v0") else ("" if cid.endswith("v1") else "none"))
    with pytest.raises(LabelImportError) as exc:
        import_labels(corpus, sheet, labeller="dan")
    assert "deploy" in str(exc.value) and "blank" in str(exc.value)
    assert not (corpus / "labels.jsonl").exists()
