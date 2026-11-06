import yaml
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Case:
    case_id: str
    human_text: str
    machine_text: str
    answer_key: list[dict]
    task_spec: dict


def load_case(corpus_dir: Path, case_id: str) -> Case:
    case_dir = corpus_dir / case_id
    human_text = (case_dir / "human.md").read_text(encoding="utf-8")
    machine_text = (case_dir / "machine.cpn").read_text(encoding="utf-8")
    answer_key = yaml.safe_load((case_dir / "answer_key.yaml").read_text(encoding="utf-8"))
    task_spec = yaml.safe_load((case_dir / "task_spec.yaml").read_text(encoding="utf-8"))
    return Case(
        case_id=case_id,
        human_text=human_text,
        machine_text=machine_text,
        answer_key=answer_key,
        task_spec=task_spec,
    )
