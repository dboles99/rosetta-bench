"""Routing-corpus tooling: family-level splits, a blind labelling sheet, and a
validated label import. Gold labels come from an independent labeller, never from a
decision provider and never from the corpus author (whose labels are kept separately,
in author_labels.jsonl, only to measure agreement)."""
from __future__ import annotations

import hashlib
import json
import random
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font
from openpyxl.worksheet.datavalidation import DataValidation

NONE_CHOICE = "none"
SHEET_HEADER = ["case_id", "request_text", "route", "unsure", "notes"]
INSTRUCTIONS = [
    "For each request choose the ONE route that fits best, from the dropdown in column C.",
    "Choose 'none' if no listed route fits what the request asks for (even if it mentions the project).",
    "Choose 'clarify' only if the request is about this project but too vague to act on.",
    "Put 'y' in column D if you are unsure. Notes are optional.",
    "Judge only from the request text and the route descriptions below.",
]


class LabelImportError(ValueError):
    pass


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _cases(corpus_dir: Path) -> list[dict]:
    return _jsonl(Path(corpus_dir) / "cases.jsonl")


def _routes(corpus_dir: Path) -> list[dict]:
    return json.loads((Path(corpus_dir) / "routes.json").read_text(encoding="utf-8"))["routes"]


def assign_splits(corpus_dir: Path, seed: int, calibration_fraction: float = 0.4) -> dict[str, str]:
    """Assign whole families to calibration or held_out, stratified by family_kind."""
    families_by_kind: dict[str, set[str]] = defaultdict(set)
    for case in _cases(corpus_dir):
        families_by_kind[case.get("family_kind", "unknown")].add(case.get("family", case["case_id"]))
    splits: dict[str, str] = {}
    for kind in sorted(families_by_kind):
        families = sorted(families_by_kind[kind])
        random.Random(f"{seed}:{kind}").shuffle(families)
        n_cal = round(len(families) * calibration_fraction)
        if len(families) >= 2:
            n_cal = min(max(n_cal, 1), len(families) - 1)
        for index, family in enumerate(families):
            splits[family] = "calibration" if index < n_cal else "held_out"
    return splits


def write_splits(corpus_dir: Path, seed: int, calibration_fraction: float = 0.4) -> dict:
    path = Path(corpus_dir) / "splits.json"
    if path.exists():
        raise FileExistsError(f"{path} exists; splits are frozen once written")
    families = assign_splits(corpus_dir, seed, calibration_fraction)
    data = {
        "seed": seed,
        "calibration_fraction": calibration_fraction,
        "unit": "family",
        "families": families,
        "hash": _sha(json.dumps({"seed": seed, "families": families}, sort_keys=True)),
        "written_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return data


def load_splits(corpus_dir: Path) -> dict:
    return json.loads((Path(corpus_dir) / "splits.json").read_text(encoding="utf-8"))


def export_labelling_sheet(corpus_dir: Path, out_path: Path, seed: int) -> Path:
    """A blind sheet: request text only, shuffled, no family, kind or author label."""
    routes = _routes(corpus_dir)
    rows = [(case["case_id"], case["request_text"]) for case in _cases(corpus_dir)]
    random.Random(seed).shuffle(rows)
    choices = [route["id"] for route in routes] + [NONE_CHOICE]

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "label"
    sheet.append(SHEET_HEADER)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    for case_id, text in rows:
        sheet.append([case_id, text, None, None, None])
    for row in sheet.iter_rows(min_row=2):
        row[1].alignment = Alignment(wrap_text=True, vertical="top")
    sheet.column_dimensions["A"].width = 10
    sheet.column_dimensions["B"].width = 90
    sheet.column_dimensions["C"].width = 20
    sheet.column_dimensions["D"].width = 8
    sheet.column_dimensions["E"].width = 40
    sheet.freeze_panes = "C2"
    validation = DataValidation(type="list", formula1='"' + ",".join(choices) + '"', allow_blank=True)
    validation.error = "Choose one of the listed routes, or none."
    sheet.add_data_validation(validation)
    validation.add(f"C2:C{len(rows) + 1}")

    reference = workbook.create_sheet("routes")
    for line in INSTRUCTIONS:
        reference.append([line])
    reference.append([])
    reference.append(["route", "description"])
    for route in routes:
        reference.append([route["id"], route["description"]])
    reference.append([NONE_CHOICE, "No listed route fits the request."])
    reference.column_dimensions["A"].width = 22
    reference.column_dimensions["B"].width = 100

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(out_path)
    return out_path


def _kappa(pairs: list[tuple[str, str]]) -> float | None:
    if not pairs:
        return None
    observed = sum(a == b for a, b in pairs) / len(pairs)
    first, second = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    expected = sum(first[k] * second[k] for k in first) / (len(pairs) ** 2)
    return 1.0 if expected == 1 else (observed - expected) / (1 - expected)


def import_labels(corpus_dir: Path, sheet_path: Path, labeller: str) -> dict:
    corpus_dir = Path(corpus_dir)
    out = corpus_dir / "labels.jsonl"
    if out.exists():
        raise FileExistsError(f"{out} exists; gold labels are frozen once imported")
    route_ids = {route["id"] for route in _routes(corpus_dir)}
    case_ids = [case["case_id"] for case in _cases(corpus_dir)]
    sheet = openpyxl.load_workbook(sheet_path, read_only=True)["label"]
    header = [cell.value for cell in next(sheet.iter_rows(max_row=1))]
    if header[: len(SHEET_HEADER)] != SHEET_HEADER:
        raise LabelImportError(f"unexpected header {header}")

    problems: list[str] = []
    labels: dict[str, dict] = {}
    for row in sheet.iter_rows(min_row=2, values_only=True):
        case_id, _, route, unsure, notes = (list(row) + [None] * 5)[:5]
        if case_id is None:
            continue
        choice = str(route).strip().lower() if route is not None else ""
        if not choice:
            problems.append(f"{case_id}: blank route")
            continue
        if choice != NONE_CHOICE and choice not in route_ids:
            problems.append(f"{case_id}: unknown route {choice!r}")
            continue
        if case_id in labels:
            problems.append(f"{case_id}: duplicate row")
            continue
        labels[case_id] = {
            "case_id": case_id,
            "label_fits": choice != NONE_CHOICE,
            "label_route": None if choice == NONE_CHOICE else choice,
            "label_source": labeller,
            "unsure": str(unsure).strip().lower() in ("y", "yes", "true", "1") if unsure is not None else False,
            "notes": str(notes) if notes else None,
        }
    missing = [cid for cid in case_ids if cid not in labels]
    unknown = [cid for cid in labels if cid not in set(case_ids)]
    problems += [f"{cid}: missing from sheet" for cid in missing] + [f"{cid}: not in corpus" for cid in unknown]
    if problems:
        raise LabelImportError("; ".join(problems[:40]) + (f" (+{len(problems) - 40} more)" if len(problems) > 40 else ""))

    text = "".join(json.dumps(labels[cid], ensure_ascii=False) + "\n" for cid in case_ids)
    out.write_text(text, encoding="utf-8", newline="\n")

    summary: dict = {
        "cases": len(case_ids),
        "labeller": labeller,
        "routes": dict(Counter(labels[cid]["label_route"] or NONE_CHOICE for cid in case_ids)),
        "unsure": sum(labels[cid]["unsure"] for cid in case_ids),
        "labels_sha256": _sha(text),
        "sheet_sha256": hashlib.sha256(Path(sheet_path).read_bytes()).hexdigest(),
        "imported_at": datetime.now(timezone.utc).isoformat(),
    }
    author_path = corpus_dir / "author_labels.jsonl"
    if author_path.exists():
        author = {a["case_id"]: (a["label_route"] or NONE_CHOICE) for a in _jsonl(author_path)}
        pairs = [((labels[cid]["label_route"] or NONE_CHOICE), author[cid]) for cid in case_ids if cid in author]
        summary["agreement_with_author"] = sum(a == b for a, b in pairs) / len(pairs) if pairs else None
        summary["kappa_with_author"] = _kappa(pairs)
        summary["disagreements"] = [cid for cid in case_ids if cid in author and (labels[cid]["label_route"] or NONE_CHOICE) != author[cid]]
    (corpus_dir / "labels_meta.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return summary
