from rosetta_bench.corpus import Case
from rosetta_bench.harness import run_comprehension
from rosetta_bench.models import RunResult
from rosetta_bench.scoring.comprehension import (
    answers_match,
    build_comprehension_prompt,
    parse_numbered_answers,
    score_comprehension,
)

KEY = [
    {"question": "What is TASK?", "answer": "ROSETTA_BUILD"},
    {"question": "What does FIELD_VALUE_TYPES list?", "answer": "str,int,float"},
]


def test_prompt_numbers_every_question_after_the_document():
    prompt = build_comprehension_prompt("DOCUMENT TEXT", KEY)
    assert prompt.startswith("DOCUMENT TEXT")
    assert "1. What is TASK?" in prompt
    assert "2. What does FIELD_VALUE_TYPES list?" in prompt


def test_answers_are_parsed_by_number():
    assert parse_numbered_answers("1. ROSETTA_BUILD\n2) str, int, float\n", 2) == ["ROSETTA_BUILD", "str, int, float"]


def test_answers_out_of_order_are_matched_by_number():
    assert parse_numbered_answers("2. b\n1. a\n", 2) == ["a", "b"]


def test_missing_answers_are_none():
    assert parse_numbered_answers("1. ROSETTA_BUILD", 2) == ["ROSETTA_BUILD", None]


def test_exact_match_ignores_case_quotes_and_list_spacing():
    assert answers_match("`str, int, float`.", "str,int,float")
    assert answers_match("rosetta_build", "ROSETTA_BUILD")


def test_exact_match_rejects_different_values():
    assert not answers_match("str,int", "str,int,float")
    assert not answers_match(None, "str,int,float")


def test_score_reports_accuracy_and_items():
    result = score_comprehension("1. rosetta_build\n2. str,int\n", KEY)
    assert result.accuracy == 0.5
    assert result.items[0].correct is True
    assert result.items[1].correct is False
    assert result.items[1].got == "str,int"


class RecordingRunner:
    name = "FAKE"
    model = "fake-1"

    def __init__(self):
        self.prompts = []
        self.tasks = []

    def run(self, prompt_text, task):
        self.prompts.append(prompt_text)
        self.tasks.append(task)
        return RunResult(raw_output="1. ROSETTA_BUILD\n2. str,int,float", tokens_in=5, tokens_out=5, latency_ms=1.0)


def test_run_comprehension_sends_the_questions_and_scores_the_reply():
    case = Case(
        case_id="c1",
        human_text="# Human",
        machine_text="SCHEMA_VER=1.0\nTASK=ROSETTA_BUILD\n",
        answer_key=KEY,
        task_spec={"name": "n", "instructions": "i"},
    )
    runner = RecordingRunner()
    outcome = run_comprehension(runner, case, "MACHINE")
    assert runner.prompts[0].startswith("SCHEMA_VER=1.0")
    assert "1. What is TASK?" in runner.prompts[0]
    assert runner.tasks == [None]
    assert outcome.score.accuracy == 1.0
    assert outcome.run_result.tokens_in == 5
