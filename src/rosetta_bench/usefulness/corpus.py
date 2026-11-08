import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from rosetta_core.loader import load_prompt


@dataclass(frozen=True)
class UsefulnessTask:
    task_id: str
    kind: str  # "code" (hidden tests decide) or "no_code" (success = no code produced)
    language: str
    entry_point: str | None
    request_text: str
    expected_route: str | None


def load_tasks(corpus_dir: Path) -> list[UsefulnessTask]:
    lines = (Path(corpus_dir) / "tasks.jsonl").read_text(encoding="utf-8").splitlines()
    return [UsefulnessTask(**json.loads(line)) for line in lines if line.strip()]


def hidden_tests(corpus_dir: Path, task: UsefulnessTask) -> str:
    return (Path(corpus_dir) / "hidden_tests" / f"test_{task.task_id}.py").read_text(encoding="utf-8")


def route_ids(corpus_dir: Path) -> list[str]:
    return sorted(p.name for p in (Path(corpus_dir) / "routes").iterdir() if p.is_dir())


def route_contract(corpus_dir: Path, route_id: str, prompt_format: str) -> str:
    """HUMAN: the Markdown view. MACHINE: rosetta-core's loader (valid packet first,
    Markdown only as a full replacement), exactly as a Rosetta consumer would load it."""
    folder = Path(corpus_dir) / "routes" / route_id
    if prompt_format == "HUMAN":
        return (folder / f"{route_id}.md").read_text(encoding="utf-8")
    schema = json.loads((folder / f"{route_id}.schema.json").read_text(encoding="utf-8"))
    return load_prompt(route_id, folder, schema)


def corpus_digest(corpus_dir: Path) -> str:
    corpus_dir = Path(corpus_dir)
    digest = hashlib.sha256()
    for path in sorted(p for p in corpus_dir.rglob("*") if p.is_file() and p.suffix in (".jsonl", ".py", ".cpn", ".md", ".json")):
        digest.update(str(path.relative_to(corpus_dir)).replace("\\", "/").encode())
        digest.update(path.read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8"))
    return digest.hexdigest()
