from rosetta_bench.models import RunResult, Task
from rosetta_bench.runners.base import Runner


class FakeRunner:
    name = "FAKE"
    model = "fake-model-v1"

    def run(self, prompt_text: str, task: Task | None) -> RunResult:
        return RunResult(raw_output=f"echo: {prompt_text}", tokens_in=1, tokens_out=1, latency_ms=0.1)


def test_fake_runner_satisfies_runner_protocol():
    runner: Runner = FakeRunner()
    result = runner.run("hello", None)
    assert result.raw_output == "echo: hello"


def test_runner_protocol_is_structural_not_nominal():
    # FakeRunner never inherits from Runner -- conformance is structural (duck-typed),
    # verified via isinstance() at runtime because Runner is @runtime_checkable.
    # issubclass() is intentionally not used here: a Protocol with non-method
    # members (name/model are data attributes, not methods) doesn't support it.
    assert Runner not in FakeRunner.__bases__
    assert isinstance(FakeRunner(), Runner)
