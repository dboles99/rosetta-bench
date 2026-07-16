"""Azure Translation runner. Suite A (comprehension) only -- Azure Translation
doesn't accept arbitrary task instructions, so `run()` raises if given a Task,
per the spec's documented asymmetry. `AzureTranslatorSDKClient` makes a live
network call -- not covered by the automated test suite (requires
AZURE_TRANSLATOR_API_KEY). `AzureTranslationRunner` is fully tested via a fake
client.
"""
import time
from typing import Protocol

from rosetta_bench.models import RunResult, Task


class AzureTranslationClientProtocol(Protocol):
    def translate(self, text: str, to_language: str) -> str:
        ...


class AzureTranslationRunner:
    name = "AZURE_TRANSLATION"

    def __init__(self, client: AzureTranslationClientProtocol, round_trip_language: str = "fr"):
        self.client = client
        self.model = round_trip_language

    def run(self, prompt_text: str, task: Task | None) -> RunResult:
        if task is not None:
            raise ValueError("AzureTranslationRunner is Suite A only and does not accept a Task")
        start = time.perf_counter()
        forward_text = self.client.translate(prompt_text, self.model)
        back_text = self.client.translate(forward_text, "en")
        latency_ms = (time.perf_counter() - start) * 1000
        return RunResult(
            raw_output=back_text,
            tokens_in=len(prompt_text.split()),
            tokens_out=len(back_text.split()),
            latency_ms=latency_ms,
            turns=2,
        )


class AzureTranslatorSDKClient:
    """Live adapter around the Azure Translator REST API. Not covered by tests."""

    def __init__(self, api_key: str, endpoint: str, region: str):
        self._api_key = api_key
        self._endpoint = endpoint.rstrip("/")
        self._region = region

    def translate(self, text: str, to_language: str) -> str:
        import json
        import urllib.request

        url = f"{self._endpoint}/translate?api-version=3.0&to={to_language}"
        payload = json.dumps([{"text": text}]).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Ocp-Apim-Subscription-Key": self._api_key,
                "Ocp-Apim-Subscription-Region": self._region,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data[0]["translations"][0]["text"]
