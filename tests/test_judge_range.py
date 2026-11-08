import pytest

from rosetta_bench.judge import parse_judge_response


def test_judge_scores_outside_one_to_five_are_rejected():
    response = "CORRECTNESS: 9\nCOMPLETENESS: 4\nFAITHFULNESS: 4\nCLARITY: 4\nJUSTIFICATION: x\n"
    with pytest.raises(ValueError):
        parse_judge_response(response)


def test_judge_score_of_zero_is_rejected():
    response = "CORRECTNESS: 0\nCOMPLETENESS: 4\nFAITHFULNESS: 4\nCLARITY: 4\nJUSTIFICATION: x\n"
    with pytest.raises(ValueError):
        parse_judge_response(response)
