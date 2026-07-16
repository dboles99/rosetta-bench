import pytest
from rosetta_bench.judge import build_judge_prompt, parse_judge_response, score_trial, JudgeResult

CANNED_RESPONSE = (
    "CORRECTNESS: 4\n"
    "COMPLETENESS: 5\n"
    "FAITHFULNESS: 3\n"
    "CLARITY: 4\n"
    "JUSTIFICATION: The output correctly addressed the task but missed one\n"
    "edge case mentioned in the constraints.\n"
)


def test_build_judge_prompt_includes_task_and_output():
    prompt = build_judge_prompt("do the thing", "here is my output", reference_output=None)
    assert "do the thing" in prompt
    assert "here is my output" in prompt


def test_build_judge_prompt_includes_reference_when_present():
    prompt = build_judge_prompt("do the thing", "output", reference_output="expected answer")
    assert "expected answer" in prompt


def test_parse_judge_response_extracts_all_scores_and_multiline_justification():
    result = parse_judge_response(CANNED_RESPONSE)
    assert result.correctness == 4
    assert result.completeness == 5
    assert result.faithfulness == 3
    assert result.clarity == 4
    assert "missed one" in result.justification
    assert "edge case" in result.justification


def test_judge_result_mean_score():
    result = JudgeResult(correctness=4, completeness=5, faithfulness=3, clarity=4, justification="")
    assert result.mean_score == 4.0


def test_score_trial_calls_call_fn_with_built_prompt_and_parses_result():
    captured_prompts = []

    def fake_call_fn(prompt: str) -> str:
        captured_prompts.append(prompt)
        return CANNED_RESPONSE

    result = score_trial("do the thing", "my output", None, fake_call_fn)
    assert result.correctness == 4
    assert len(captured_prompts) == 1
    assert "do the thing" in captured_prompts[0]


def test_parse_judge_response_raises_on_missing_field():
    with pytest.raises(KeyError):
        parse_judge_response("CORRECTNESS: 4\nJUSTIFICATION: incomplete response\n")
