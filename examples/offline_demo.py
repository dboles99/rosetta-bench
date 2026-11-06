"""Run the harness end to end with no network and no API key.

The "model" here is a stub that echoes the length of the prompt it was given,
so the numbers printed are properties of the corpus files, not of any LLM.
Replace StubRunner with ClaudeRunner(model, AnthropicSDKClient(key)) (or one of
the other runners) to measure a real model.

Run from the repository root:  python examples/offline_demo.py
"""
import tempfile
from pathlib import Path

from rosetta_bench.corpus import load_case
from rosetta_bench.export_xlsx import export_to_xlsx
from rosetta_bench.harness import run_trial
from rosetta_bench.models import RunResult, Task
from rosetta_bench.storage import append_trial, load_trials


class StubRunner:
    name = "STUB"
    model = "stub-1"

    def run(self, prompt_text: str, task: Task | None) -> RunResult:
        chars = len(prompt_text)
        return RunResult(
            raw_output=f"stub answer for a prompt of {chars} characters",
            tokens_in=chars,  # characters, standing in for tokens
            tokens_out=8,
            latency_ms=0.0,
        )


def stub_judge(_prompt: str) -> str:
    return "CORRECTNESS: 3\nCOMPLETENESS: 3\nFAITHFULNESS: 3\nCLARITY: 3\nJUSTIFICATION: stub judge, fixed scores.\n"


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    case = load_case(root / "corpus", "rosetta_build")
    out_dir = Path(tempfile.mkdtemp(prefix="rosetta-bench-demo-"))
    csv_path = out_dir / "trials.csv"

    for i, fmt in enumerate(("HUMAN", "MACHINE"), start=1):
        trial = run_trial(StubRunner(), case, fmt, "TASK_COMPLETION", stub_judge,
                          f"demo-{i}", "2026-01-01T00:00:00Z")
        append_trial(trial, csv_path)

    for row in load_trials(csv_path):
        print(f"{row['prompt_format']:8} prompt characters: {row['tokens_in']}")

    export_to_xlsx(csv_path, out_dir / "trials.xlsx")
    print(f"wrote {csv_path} and {out_dir / 'trials.xlsx'}")


if __name__ == "__main__":
    main()
