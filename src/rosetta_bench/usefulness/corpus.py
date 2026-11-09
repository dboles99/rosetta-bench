import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from rosetta_core.human_doc import extract_notes
from rosetta_core.loader import load_prompt


KINDS = ("code", "no_code", "docs_edit", "translation_review", "data_query", "clarify", "unsolvable", "false_premise", "defect")
SOLVABLE_KINDS = ("code", "docs_edit", "translation_review", "data_query", "clarify")


@dataclass(frozen=True)
class UsefulnessTask:
    task_id: str
    kind: str  # one of KINDS; the verifier registry (verify.py) decides success per kind
    language: str
    entry_point: str | None
    request_text: str
    expected_route: str | None
    check: dict = field(default_factory=dict, hash=False)  # kind-specific success parameters
    tags: tuple = ()  # e.g. kobayashi_maru, true_premise_control, nowin_near_miss


def load_tasks(corpus_dir: Path) -> list[UsefulnessTask]:
    lines = (Path(corpus_dir) / "tasks.jsonl").read_text(encoding="utf-8").splitlines()
    tasks = []
    for line in lines:
        if line.strip():
            raw = json.loads(line)
            raw["tags"] = tuple(raw.get("tags", ()))
            raw["check"] = raw.get("check") or {}
            tasks.append(UsefulnessTask(**raw))
    return tasks


def hidden_tests(corpus_dir: Path, task: UsefulnessTask) -> str:
    return (Path(corpus_dir) / "hidden_tests" / f"test_{task.task_id}.py").read_text(encoding="utf-8")


def corpus_config(corpus_dir: Path) -> dict:
    """Optional corpus.json: baseline_route (the route used without a decision layer, default
    code_change) and catalogue_exclude (routes a decider may not choose, e.g. that baseline)."""
    path = Path(corpus_dir) / "corpus.json"
    config = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    return {"baseline_route": config.get("baseline_route", "code_change"),
            "catalogue_exclude": list(config.get("catalogue_exclude", []))}


def route_ids(corpus_dir: Path) -> list[str]:
    return sorted(p.name for p in (Path(corpus_dir) / "routes").iterdir() if p.is_dir())


REPRESENTATIONS = {
    "P": "plain prose prompt (the contract's hand-written notes, no Rosetta structure)",
    "H": "Rosetta human view (.md: generated field list plus notes)",
    "M": "Rosetta machine view (.cpn packet, loaded by rosetta_core.loader)",
    "R": "reason-first: a planner (reasoning on) writes a plan, rosetta-core compiles it into a canonical packet, "
         "and the executor (reasoning off) follows the M contract plus the plan",
}
_ALIASES = {"PLAIN": "P", "HUMAN": "H", "MACHINE": "M"}


def route_contract(corpus_dir: Path, route_id: str, representation: str) -> str:
    """P: plain prose from the notes region (extracted by rosetta-core). H: the Markdown
    view. M: rosetta-core's loader (valid packet first, Markdown only as a full
    replacement), exactly as a Rosetta consumer would load it."""
    rep = _ALIASES.get(representation, representation)
    folder = Path(corpus_dir) / "routes" / route_id
    markdown = (folder / f"{route_id}.md").read_text(encoding="utf-8")
    if rep == "P":
        return extract_notes(markdown) + "\n"
    if rep == "H":
        return markdown
    if rep == "M":
        schema = json.loads((folder / f"{route_id}.schema.json").read_text(encoding="utf-8"))
        return load_prompt(route_id, folder, schema)
    raise ValueError(f"unknown representation {representation!r}")


def corpus_digest(corpus_dir: Path) -> str:
    corpus_dir = Path(corpus_dir)
    digest = hashlib.sha256()
    for path in sorted(p for p in corpus_dir.rglob("*") if p.is_file() and p.suffix in (".jsonl", ".py", ".cpn", ".md", ".json")):
        digest.update(str(path.relative_to(corpus_dir)).replace("\\", "/").encode())
        digest.update(path.read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8"))
    return digest.hexdigest()
