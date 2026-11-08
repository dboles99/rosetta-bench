"""Deterministic offline stand-in for a generator. SYNTHETIC: its outputs describe
the corpus files, never any model. It exists to exercise wiring and scoring."""
import re

from rosetta_bench.models import RunResult, Task
from rosetta_bench.scoring.comprehension import INSTRUCTION

_FIELD_LINE = re.compile(r"^(?:-\s*)?([A-Z][A-Z0-9_]+)\s*[=:]\s*(.+?)\s*$", re.MULTILINE)
_QUESTION_LINE = re.compile(r"^(\d+)\.\s+(.*)$", re.MULTILINE)
_KEY_TOKEN = re.compile(r"\b[A-Z][A-Z0-9_]{2,}\b")


class FakeGenerator:
    name = "FAKE"

    def __init__(self, model: str):
        self.model = model

    @staticmethod
    def _fields(document: str) -> dict[str, str]:
        fields: dict[str, str] = {}
        for key, value in _FIELD_LINE.findall(document):
            fields.setdefault(key, value)
        return fields

    def _answer_questions(self, prompt: str) -> str:
        document, _, questions = prompt.partition(INSTRUCTION)
        if not questions:
            document = questions = prompt
        fields = self._fields(document)
        lines = []
        for number, question in _QUESTION_LINE.findall(questions):
            keys = [token for token in _KEY_TOKEN.findall(question) if token in fields]
            lines.append(f"{number}. {fields[keys[0]] if keys else 'unknown'}")
        return "\n".join(lines)

    def _summarise(self, document: str, instructions: str) -> str:
        fields = self._fields(document)
        named = [token for token in dict.fromkeys(_KEY_TOKEN.findall(instructions)) if token in fields]
        return "\n".join(f"- {key}: {fields[key]}" for key in named[:3])

    def run(self, prompt_text: str, task: Task | None) -> RunResult:
        if task is None:
            output = self._answer_questions(prompt_text)
        else:
            output = self._summarise(prompt_text, task.instructions)
        sent = prompt_text if task is None else f"{prompt_text}\n\nTask: {task.instructions}"  # as real runners send it
        return RunResult(
            raw_output=output,
            tokens_in=len(sent.split()),  # whitespace words, not provider tokens
            tokens_out=len(output.split()),
            latency_ms=0.0,
        )
