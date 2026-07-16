from typing import Protocol, runtime_checkable

from rosetta_bench.models import RunResult, Task


@runtime_checkable
class Runner(Protocol):
    name: str
    model: str

    def run(self, prompt_text: str, task: Task | None) -> RunResult:
        ...
