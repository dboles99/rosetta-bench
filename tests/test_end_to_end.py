from pathlib import Path
from rosetta_bench.corpus import load_case
from rosetta_bench.export_xlsx import export_to_xlsx
from rosetta_bench.harness import run_trial
from rosetta_bench.models import RunResult, Task
from rosetta_bench.storage import append_trial, load_trials


class FakeRunner:
    def __init__(self, name: str, model: str, response_text: str):
        self.name = name
        self.model = model
        self.response_text = response_text

    def run(self, prompt_text: str, task: Task | None) -> RunResult:
        return RunResult(raw_output=self.response_text, tokens_in=20, tokens_out=10, latency_ms=50.0)


def _fake_judge(prompt: str) -> str:
    return "CORRECTNESS: 5\nCOMPLETENESS: 5\nFAITHFULNESS: 4\nCLARITY: 5\nJUSTIFICATION: Good summary.\n"


def test_full_lifecycle_load_corpus_run_both_formats_export(tmp_path: Path):
    corpus_dir = Path("corpus")
    case = load_case(corpus_dir, "rosetta_build")

    csv_path = tmp_path / "trials.csv"
    runner_human = FakeRunner("CLAUDE", "claude-sonnet-5", "summary using human doc")
    runner_machine = FakeRunner("CLAUDE", "claude-sonnet-5", "summary using machine packet")

    trial_human = run_trial(runner_human, case, "HUMAN", "TASK_COMPLETION", _fake_judge, "t1", "2026-07-13T00:00:00Z")
    trial_machine = run_trial(runner_machine, case, "MACHINE", "TASK_COMPLETION", _fake_judge, "t2", "2026-07-13T00:00:01Z")
    append_trial(trial_human, csv_path)
    append_trial(trial_machine, csv_path)

    rows = load_trials(csv_path)
    assert len(rows) == 2
    assert {r["prompt_format"] for r in rows} == {"HUMAN", "MACHINE"}
    assert all(float(r["quality_score"]) == 4.75 for r in rows)

    xlsx_path = tmp_path / "trials.xlsx"
    export_to_xlsx(csv_path, xlsx_path)
    assert xlsx_path.exists()
