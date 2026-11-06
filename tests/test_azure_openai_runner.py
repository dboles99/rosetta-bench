from rosetta_bench.models import Task
from rosetta_bench.runners.azure_openai_runner import AzureOpenAIRunner


class FakeAzureOpenAIClient:
    def __init__(self, response_text: str, input_tokens: int, output_tokens: int):
        self.response_text = response_text
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.calls: list[tuple[str, str]] = []

    def create_completion(self, deployment: str, prompt: str) -> tuple[str, int, int]:
        self.calls.append((deployment, prompt))
        return self.response_text, self.input_tokens, self.output_tokens


def test_run_without_task_sends_prompt_text_verbatim():
    client = FakeAzureOpenAIClient("the answer", 50, 10)
    runner = AzureOpenAIRunner(deployment="gpt-4o", client=client)

    result = runner.run("What is TASK?", None)

    assert result.raw_output == "the answer"
    assert result.tokens_in == 50
    assert result.tokens_out == 10
    assert client.calls == [("gpt-4o", "What is TASK?")]


def test_run_with_task_appends_instructions_to_prompt():
    client = FakeAzureOpenAIClient("done", 20, 5)
    runner = AzureOpenAIRunner(deployment="gpt-4o", client=client)
    task = Task(name="validate", instructions="write a validator function")

    runner.run("SCHEMA_VER=1.0\nTASK=X", task)

    sent_prompt = client.calls[0][1]
    assert "SCHEMA_VER=1.0" in sent_prompt
    assert "write a validator function" in sent_prompt


def test_runner_exposes_name_and_model():
    runner = AzureOpenAIRunner(deployment="gpt-4o", client=FakeAzureOpenAIClient("x", 1, 1))
    assert runner.name == "AZURE_OPENAI"
    assert runner.model == "gpt-4o"
