import io
import json

import pytest

pytest.importorskip("rosetta_core.decision", reason="needs rosetta-core")

from rosetta_bench.models import RunResult, Task
from rosetta_bench.runners import ollama_runner
from rosetta_bench.runners.ollama_runner import OllamaHTTPClient, OllamaRunner
from rosetta_bench.usefulness.reason_first import (
    PLANNER_PROMPT,
    PlanError,
    execution_prompt,
    non_proceed_output,
    parse_plan,
    plan_cache_key,
)

GOOD_PLAN = """Here is the plan.
SCHEMA_VER=1.0
VERDICT=PROCEED
ENTRY_POINT=differing_keys
SIGNATURE=def differing_keys(a: dict, b: dict) -> list
STEPS=1 union the keys | 2 compare str() of each side | 3 sort
EDGE_CASES=missing key counts as None | empty dicts
REASON=none
"""


def test_a_plan_becomes_a_canonical_validated_rosetta_packet():
    plan = parse_plan(GOOD_PLAN)
    assert plan.verdict == "PROCEED"
    assert plan.packet.startswith("SCHEMA_VER=1.0\n")
    lines = plan.packet.strip().splitlines()[1:]
    assert lines == sorted(lines)  # canonical: keys sorted, LF endings
    assert plan.fields["ENTRY_POINT"] == "differing_keys"
    assert len(plan.digest) == 64


def test_formatting_differences_give_the_same_packet():
    shuffled = "\r\n".join(reversed(GOOD_PLAN.strip().splitlines()[1:]))
    assert parse_plan(shuffled).packet == parse_plan(GOOD_PLAN).packet


@pytest.mark.parametrize("bad", [
    GOOD_PLAN.replace("VERDICT=PROCEED\n", ""),
    GOOD_PLAN.replace("VERDICT=PROCEED", "VERDICT=MAYBE"),
    "no plan at all",
])
def test_an_invalid_plan_is_refused(bad):
    with pytest.raises(PlanError):
        parse_plan(bad)


def test_a_non_proceed_verdict_needs_a_reason_and_yields_the_contract_marker():
    unsolvable = GOOD_PLAN.replace("VERDICT=PROCEED", "VERDICT=UNSOLVABLE").replace("REASON=none", "REASON=tests require f(1) to be 2 and 3")
    plan = parse_plan(unsolvable)
    assert non_proceed_output(plan) == "UNSOLVABLE: tests require f(1) to be 2 and 3"
    with pytest.raises(PlanError):
        parse_plan(GOOD_PLAN.replace("VERDICT=PROCEED", "VERDICT=PREMISE_REJECTED"))  # reason still "none"


def test_execution_prompt_carries_contract_plan_and_request_only():
    plan = parse_plan(GOOD_PLAN)
    prompt = execution_prompt("SCHEMA_VER=1.0\nROUTE=code_change\n", plan, "Write differing_keys(a, b).")
    assert "ROUTE=code_change" in prompt and plan.packet in prompt and "Write differing_keys" in prompt
    assert prompt.index("ROUTE=code_change") < prompt.index("VERDICT=PROCEED") < prompt.index("Write differing_keys")


def test_planner_prompt_forbids_code():
    assert "Do not write code" in PLANNER_PROMPT and "VERDICT=" in PLANNER_PROMPT


def test_plan_cache_key_is_canonical_and_separates_samples():
    a = plan_cache_key("Fix the café\r\nmenu", model="m", sample=0)
    assert a == plan_cache_key("Fix the café\nmenu", model="m", sample=0)
    assert a != plan_cache_key("Fix the café\nmenu", model="m", sample=1)
    assert a != plan_cache_key("Fix the café\nmenu", model="other", sample=0)


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_ollama_client_sends_think_and_reports_reasoning_size(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout=None):
        seen["body"] = json.loads(request.data)
        reply = {"response": "```python\nx = 1\n```", "thinking": "t" * 300, "prompt_eval_count": 50,
                 "eval_count": 120, "prompt_eval_cached_count": 40}
        return _Response(json.dumps(reply).encode())

    monkeypatch.setattr(ollama_runner.urllib.request, "urlopen", fake_urlopen)
    client = OllamaHTTPClient("http://localhost:11434", think=False)
    result = OllamaRunner("kimi", client).run("prompt", Task(name="t", instructions="do it"))
    assert seen["body"]["think"] is False
    # 19 visible reply characters; reasoning estimate = 120 * 300 / 319 = 112.9 -> 113
    assert result.meta == {"think": False, "reasoning_chars": 300, "response_chars": 19,
                           "prompt_cached_tokens": 40, "estimated_reasoning_tokens": 113}


def test_run_result_meta_defaults_to_empty():
    assert RunResult("x", 1, 1, 1.0).meta == {}


def test_the_planner_can_ask_for_clarification_and_the_plan_schema_is_versioned():
    from rosetta_bench.usefulness.reason_first import HANDOFF_VERDICTS, PLAN_SCHEMA_VER, REFUSING_VERDICTS

    assert PLAN_SCHEMA_VER == "1.1" and f"SCHEMA_VER={PLAN_SCHEMA_VER}" in PLANNER_PROMPT
    assert "NEEDS_CLARIFICATION" in PLANNER_PROMPT and set(HANDOFF_VERDICTS) == {"NOT_A_CODE_TASK", "NEEDS_CLARIFICATION"}
    assert set(REFUSING_VERDICTS) == {"UNSOLVABLE", "PREMISE_REJECTED", "REPORT_DEFECT"}
    plan = parse_plan("SCHEMA_VER=1.1\nVERDICT=NEEDS_CLARIFICATION\nENTRY_POINT=none\nSIGNATURE=none\nSTEPS=1 ask\n"
                      "EDGE_CASES=none\nREASON=the rules discussed earlier are not given\n")
    assert plan.verdict == "NEEDS_CLARIFICATION"
