"""Claude runner. `AnthropicSDKClient` wraps the real `anthropic` package and makes
a live network call -- it is intentionally NOT covered by the automated test suite
(requires ANTHROPIC_API_KEY). `ClaudeRunner` itself is fully tested via a fake
client implementing `AnthropicClientProtocol`.
"""
import time
from typing import Protocol

from rosetta_bench.models import RunResult, Task


class AnthropicClientProtocol(Protocol):
    def create_message(self, model: str, prompt: str) -> tuple[str, int, int]:
        """Returns (response_text, input_tokens, output_tokens)."""
        ...


class ClaudeRunner:
    name = "CLAUDE"

    def __init__(self, model: str, client: AnthropicClientProtocol):
        self.model = model
        self.client = client

    def run(self, prompt_text: str, task: Task | None) -> RunResult:
        full_prompt = prompt_text if task is None else f"{prompt_text}\n\nTask: {task.instructions}"
        start = time.perf_counter()
        response_text, tokens_in, tokens_out = self.client.create_message(self.model, full_prompt)
        latency_ms = (time.perf_counter() - start) * 1000
        return RunResult(
            raw_output=response_text,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            turns=1,
        )


class AnthropicSDKClient:
    """Live adapter around the `anthropic` package. Not covered by automated tests."""

    def __init__(self, api_key: str):
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)

    def create_message(self, model: str, prompt: str) -> tuple[str, int, int]:
        response = self._client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in response.content if hasattr(block, "text"))
        return text, response.usage.input_tokens, response.usage.output_tokens
