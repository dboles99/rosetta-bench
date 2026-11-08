"""Ollama runner. `OllamaHTTPClient` makes a live HTTP call to a local Ollama
server -- not covered by the automated test suite (requires a running server).
`OllamaRunner` is fully tested via a fake client.
"""
import json
import time
import urllib.request
from typing import Protocol

from rosetta_bench.models import RunResult, Task


class OllamaClientProtocol(Protocol):
    def generate(self, model: str, prompt: str) -> tuple[str, int, int]:
        """Returns (response_text, input_tokens, output_tokens)."""
        ...


class OllamaRunner:
    name = "OLLAMA"

    def __init__(self, model: str, client: OllamaClientProtocol):
        self.model = model
        self.client = client

    def run(self, prompt_text: str, task: Task | None) -> RunResult:
        full_prompt = prompt_text if task is None else f"{prompt_text}\n\nTask: {task.instructions}"
        start = time.perf_counter()
        response_text, tokens_in, tokens_out = self.client.generate(self.model, full_prompt)
        latency_ms = (time.perf_counter() - start) * 1000
        return RunResult(
            raw_output=response_text,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            turns=1,
        )


class OllamaHTTPClient:
    """Live adapter over Ollama's local HTTP API. Not covered by tests."""

    def __init__(self, host: str, timeout_s: float | None = 300.0, options: dict | None = None):
        self._host = host.rstrip("/")
        self.timeout_s = timeout_s  # None keeps the old wait-forever behaviour
        self.options = dict(options or {})  # e.g. {"temperature": 0, "seed": 7}; recorded in run manifests

    def generate(self, model: str, prompt: str) -> tuple[str, int, int]:
        body = {"model": model, "prompt": prompt, "stream": False}
        if self.options:
            body["options"] = self.options
        payload = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            f"{self._host}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["response"], data.get("prompt_eval_count", 0), data.get("eval_count", 0)
