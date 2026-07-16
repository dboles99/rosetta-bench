import csv
from pathlib import Path

from rosetta_bench.models import Trial

_COLUMNS = [
    "trial_id", "timestamp", "tool", "model", "prompt_id", "prompt_format",
    "suite", "tokens_in", "tokens_out", "latency_ms", "turns", "task_success",
    "comprehension_accuracy", "quality_score", "judge_justification",
    "cost_usd", "raw_output",
]


def append_trial(trial: Trial, path: Path) -> None:
    file_exists = path.exists()
    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_COLUMNS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(trial.to_row())


def load_trials(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))
