"""Azure OpenAI runner. `AzureOpenAISDKClient` makes a live network call -- not
covered by the automated test suite (requires AZURE_OPENAI_API_KEY/ENDPOINT).
`AzureOpenAIRunner` is fully tested via a fake client.
"""
import time
from typing import Protocol

from rosetta_bench.models import RunResult, Task


class AzureOpenAIClientProtocol(Protocol):
    def create_completion(self, deployment: str, prompt: str) -> tuple[str, int, int]:
        """Returns (response_text, input_tokens, output_tokens)."""
        ...


class AzureOpenAIRunner:
    name = "AZURE_OPENAI"

    def __init__(self, deployment: str, client: AzureOpenAIClientProtocol):
        self.model = deployment
        self.client = client

    def run(self, prompt_text: str, task: Task | None) -> RunResult:
        full_prompt = prompt_text if task is None else f"{prompt_text}\n\nTask: {task.instructions}"
        start = time.perf_counter()
        response_text, tokens_in, tokens_out = self.client.create_completion(self.model, full_prompt)
        latency_ms = (time.perf_counter() - start) * 1000
        return RunResult(
            raw_output=response_text,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            turns=1,
        )


class AzureOpenAISDKClient:
    """Live adapter around the `openai` package configured for Azure. Not covered by tests."""

    def __init__(self, api_key: str, endpoint: str, api_version: str = "2024-06-01"):
        from openai import AzureOpenAI

        self._client = AzureOpenAI(api_key=api_key, azure_endpoint=endpoint, api_version=api_version)

    def create_completion(self, deployment: str, prompt: str) -> tuple[str, int, int]:
        response = self._client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.choices[0].message.content or ""
        return text, response.usage.prompt_tokens, response.usage.completion_tokens
