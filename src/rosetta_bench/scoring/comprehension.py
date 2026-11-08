"""Suite A: ask the answer-key questions after the document and score exact matches.

Matching is exact after light normalisation only (case, surrounding quotes or
backticks, a trailing full stop, spacing around commas). Paraphrases do not match;
they are recorded per item so a later semantic check can review them.
"""
import re
from dataclasses import dataclass

INSTRUCTION = (
    "Answer each question below using only the document above. Reply with one line per "
    "question in the form `N. answer`, giving the exact value only."
)

_ANSWER_LINE = re.compile(r"^\s*(\d+)\s*[.):]\s*(.*?)\s*$")
_WRAPPERS = "`'\"*"


@dataclass(frozen=True)
class ComprehensionItem:
    question: str
    expected: str
    got: str | None
    correct: bool


@dataclass(frozen=True)
class ComprehensionScore:
    accuracy: float | None
    items: tuple[ComprehensionItem, ...]


def build_comprehension_prompt(document: str, answer_key: list[dict]) -> str:
    lines = [document.rstrip("\n"), "", INSTRUCTION, ""]
    lines += [f"{number}. {item['question']}" for number, item in enumerate(answer_key, start=1)]
    return "\n".join(lines) + "\n"


def parse_numbered_answers(text: str, count: int) -> list[str | None]:
    found: dict[int, str] = {}
    for line in text.splitlines():
        match = _ANSWER_LINE.match(line)
        if match:
            number = int(match.group(1))
            if 1 <= number <= count and number not in found:
                found[number] = match.group(2)
    return [found.get(number) for number in range(1, count + 1)]


def _normalise(value: str) -> str:
    text = value.strip().strip(_WRAPPERS).strip()
    text = text.rstrip(".").strip().strip(_WRAPPERS).strip()
    text = re.sub(r"\s*,\s*", ",", text)
    text = re.sub(r"\s+", " ", text)
    return text.casefold()


def answers_match(got: str | None, expected: str) -> bool:
    if got is None:
        return False
    return _normalise(got) == _normalise(str(expected))


def score_comprehension(output: str, answer_key: list[dict]) -> ComprehensionScore:
    answers = parse_numbered_answers(output, len(answer_key))
    items = tuple(
        ComprehensionItem(
            question=item["question"],
            expected=str(item["answer"]),
            got=got,
            correct=answers_match(got, item["answer"]),
        )
        for item, got in zip(answer_key, answers)
    )
    accuracy = sum(item.correct for item in items) / len(items) if items else None
    return ComprehensionScore(accuracy=accuracy, items=items)
