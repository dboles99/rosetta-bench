from rosetta_bench.models import Task
from rosetta_bench.runners.claude_runner import ClaudeRunner


class FakeAnthropicClient:
    def __init__(self, response_text: str, input_tokens: int, output_tokens: int):
        self.response_text = response_text
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.calls: list[tuple[str, str]] = []

    def create_message(self, model: str, prompt: str) -> tuple[str, int, int]:
        self.calls.append((model, prompt))
        return self.response_text, self.input_tokens, self.output_tokens


def test_run_without_task_sends_prompt_text_verbatim():
    client = FakeAnthropicClient("the answer", 50, 10)
    runner = ClaudeRunner(model="claude-sonnet-5", client=client)

    result = runner.run("What is TASK?", None)

    assert result.raw_output == "the answer"
    assert result.tokens_in == 50
    assert result.tokens_out == 10
    assert result.latency_ms >= 0
    assert client.calls == [("claude-sonnet-5", "What is TASK?")]


def test_run_with_task_appends_instructions_to_prompt():
    client = FakeAnthropicClient("done", 20, 5)
    runner = ClaudeRunner(model="claude-sonnet-5", client=client)
    task = Task(name="validate", instructions="write a validator function")

    runner.run("SCHEMA_VER=1.0\nTASK=X", task)

    sent_prompt = client.calls[0][1]
    assert "SCHEMA_VER=1.0" in sent_prompt
    assert "write a validator function" in sent_prompt


def test_runner_exposes_name_and_model():
    runner = ClaudeRunner(model="claude-sonnet-5", client=FakeAnthropicClient("x", 1, 1))
    assert runner.name == "CLAUDE"
    assert runner.model == "claude-sonnet-5"
