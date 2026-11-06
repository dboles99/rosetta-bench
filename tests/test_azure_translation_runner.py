import pytest
from rosetta_bench.models import Task
from rosetta_bench.runners.azure_translation_runner import AzureTranslationRunner


class FakeTranslationClient:
    def __init__(self, forward_text: str, back_text: str):
        self.forward_text = forward_text
        self.back_text = back_text
        self.calls: list[tuple[str, str]] = []

    def translate(self, text: str, to_language: str) -> str:
        self.calls.append((text, to_language))
        return self.back_text if to_language == "en" else self.forward_text


def test_run_performs_round_trip_translation():
    client = FakeTranslationClient(forward_text="texte franc", back_text="round tripped text")
    runner = AzureTranslationRunner(client=client, round_trip_language="fr")

    result = runner.run("SCHEMA_VER=1.0\nTASK=X", None)

    assert result.raw_output == "round tripped text"
    assert client.calls == [("SCHEMA_VER=1.0\nTASK=X", "fr"), ("texte franc", "en")]


def test_run_rejects_a_task_since_this_runner_is_suite_a_only():
    client = FakeTranslationClient(forward_text="x", back_text="y")
    runner = AzureTranslationRunner(client=client)
    task = Task(name="validate", instructions="write a validator function")

    with pytest.raises(ValueError, match="Suite A"):
        runner.run("some prompt", task)


def test_runner_exposes_name_and_model():
    runner = AzureTranslationRunner(client=FakeTranslationClient("x", "y"), round_trip_language="de")
    assert runner.name == "AZURE_TRANSLATION"
    assert runner.model == "de"
