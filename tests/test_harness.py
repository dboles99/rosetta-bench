from rosetta_bench.corpus import Case
from rosetta_bench.harness import run_trial
from rosetta_bench.models import RunResult, Task


class FakeRunner:
    name = "FAKE"
    model = "fake-model-v1"

    def __init__(self, response_text: str = "fake output"):
        self.response_text = response_text
        self.received_tasks: list[Task | None] = []

    def run(self, prompt_text: str, task) -> RunResult:
        self.received_tasks.append(task)
        return RunResult(raw_output=self.response_text, tokens_in=10, tokens_out=5, latency_ms=42.0)


def _make_case() -> Case:
    return Case(
        case_id="rosetta_build",
        human_text="# Human doc",
        machine_text="SCHEMA_VER=1.0\nTASK=X",
        answer_key=[{"question": "What is TASK?", "answer": "X"}],
        task_spec={"name": "validate", "instructions": "write a validator", "reference_output": None},
    )


def test_comprehension_trial_sends_no_task_and_selects_machine_text():
    runner = FakeRunner()
    case = _make_case()

    trial = run_trial(runner, case, "MACHINE", "COMPREHENSION", judge_call_fn=None, trial_id="t1", timestamp="2026-07-13T00:00:00Z")

    assert runner.received_tasks == [None]
    assert trial.prompt_format == "MACHINE"
    assert trial.suite == "COMPREHENSION"
    assert trial.comprehension_accuracy is None
    assert trial.quality_score is None
    assert trial.tool == "FAKE"
    assert trial.cost_usd == 0.0  # unknown (tool, model) pair per pricing.py


def test_task_completion_trial_sends_task_built_from_case_spec():
    runner = FakeRunner()
    case = _make_case()

    trial = run_trial(runner, case, "HUMAN", "TASK_COMPLETION", judge_call_fn=None, trial_id="t2", timestamp="2026-07-13T00:00:00Z")

    assert runner.received_tasks[0].instructions == "write a validator"
    assert trial.prompt_format == "HUMAN"
    assert trial.suite == "TASK_COMPLETION"


def test_task_completion_trial_invokes_judge_when_provided():
    runner = FakeRunner(response_text="my validator implementation")

    def fake_judge_call_fn(prompt: str) -> str:
        assert "my validator implementation" in prompt
        return "CORRECTNESS: 5\nCOMPLETENESS: 4\nFAITHFULNESS: 5\nCLARITY: 4\nJUSTIFICATION: Solid.\n"

    case = _make_case()
    trial = run_trial(runner, case, "HUMAN", "TASK_COMPLETION", judge_call_fn=fake_judge_call_fn, trial_id="t3", timestamp="2026-07-13T00:00:00Z")

    assert trial.quality_score == 4.5
    assert "Solid" in trial.judge_justification
