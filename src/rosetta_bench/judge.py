from dataclasses import dataclass
from typing import Callable

JudgeCallFn = Callable[[str], str]

_SCORE_FIELDS = ("CORRECTNESS", "COMPLETENESS", "FAITHFULNESS", "CLARITY")


@dataclass
class JudgeResult:
    correctness: int
    completeness: int
    faithfulness: int
    clarity: int
    justification: str

    @property
    def mean_score(self) -> float:
        return (self.correctness + self.completeness + self.faithfulness + self.clarity) / 4


def build_judge_prompt(task_instructions: str, raw_output: str, reference_output: str | None) -> str:
    reference_block = f"\nReference/expected output:\n{reference_output}\n" if reference_output else ""
    return (
        "You are scoring an AI system's output against a rubric. Score each dimension 1-5.\n\n"
        f"Task instructions:\n{task_instructions}\n"
        f"{reference_block}\n"
        f"Output to score:\n{raw_output}\n\n"
        "Respond with exactly this format, one line each, justification may span multiple lines:\n"
        "CORRECTNESS: <1-5>\n"
        "COMPLETENESS: <1-5>\n"
        "FAITHFULNESS: <1-5>\n"
        "CLARITY: <1-5>\n"
        "JUSTIFICATION: <explanation>"
    )


def parse_judge_response(response_text: str) -> JudgeResult:
    scores: dict[str, int] = {}
    justification_lines: list[str] = []
    in_justification = False
    for line in response_text.splitlines():
        if line.startswith("JUSTIFICATION:"):
            in_justification = True
            justification_lines.append(line[len("JUSTIFICATION:"):].strip())
            continue
        if in_justification:
            if line.strip():
                justification_lines.append(line.strip())
            continue
        for field in _SCORE_FIELDS:
            if line.startswith(f"{field}:"):
                scores[field] = int(line[len(field) + 1:].strip())

    missing = [f for f in _SCORE_FIELDS if f not in scores]
    if missing:
        raise KeyError(f"judge response missing fields: {missing}")
    out_of_range = [f for f in _SCORE_FIELDS if not 1 <= scores[f] <= 5]
    if out_of_range:
        raise ValueError(f"judge scores outside 1-5: {out_of_range}")

    return JudgeResult(
        correctness=scores["CORRECTNESS"],
        completeness=scores["COMPLETENESS"],
        faithfulness=scores["FAITHFULNESS"],
        clarity=scores["CLARITY"],
        justification=" ".join(justification_lines).strip(),
    )


def score_trial(
    task_instructions: str,
    raw_output: str,
    reference_output: str | None,
    call_fn: JudgeCallFn,
) -> JudgeResult:
    prompt = build_judge_prompt(task_instructions, raw_output, reference_output)
    response_text = call_fn(prompt)
    return parse_judge_response(response_text)
