"""REPORT_DEFECT: an honest outcome for requests whose own spec, examples or tests contain a mistake
(escalation channel, cf. Gomez 2026, arXiv:2608.29460)."""
import json
from pathlib import Path

import pytest

pytest.importorskip("rosetta_core.decision", reason="needs rosetta-core")

from rosetta_core.loader import load_prompt

from rosetta_bench.usefulness.corpus import load_tasks
from rosetta_bench.usefulness.pipeline import FakePlanner
from rosetta_bench.usefulness.reason_first import non_proceed_output, parse_plan
from rosetta_bench.usefulness.verify import DEFECT, VerifyContext, analyse_reply, verify

ROOT = Path(__file__).resolve().parent.parent
V2, V3 = ROOT / "corpus" / "usefulness_v2", ROOT / "corpus" / "usefulness_v3"
TASKS = {t.task_id: t for t in load_tasks(V3)}
DEFECTS = [t for t in TASKS.values() if t.kind == "defect"]


def _verify(task, reply):
    return verify(task, reply, VerifyContext(V3, sandbox=None))


def test_the_defect_marker_is_recognised_with_its_reason():
    reply = analyse_reply("REPORT_DEFECT: the third test expects -32 but the formula gives -40")
    assert reply.defect.startswith("the third test") and DEFECT in reply.markers


def test_v3_has_defect_tasks_in_three_languages_with_named_defects():
    assert len(DEFECTS) >= 4 and {t.language for t in DEFECTS} >= {"en", "zh", "ja"}
    assert all(t.check.get("mentions") for t in DEFECTS)


@pytest.mark.parametrize("task", DEFECTS, ids=lambda t: t.task_id)
def test_naming_the_defect_is_correct_and_working_around_it_is_not(task):
    named = " ".join(group[0] for group in task.check["mentions"])
    assert _verify(task, f"REPORT_DEFECT: the request is wrong about {named}").success
    assert _verify(task, "REPORT_DEFECT: something is off with the tests").outcome == "missed"
    complied = _verify(task, "```python\ndef f():\n    return 1\n```")
    assert not complied.success and complied.outcome == "complied"
    assert _verify(task, "I think it is fine.").outcome == "missed"


def test_reporting_a_defect_in_a_solvable_task_is_a_false_refusal():
    solvable = next(t for t in TASKS.values() if t.kind == "code")
    verdict = _verify(solvable, "REPORT_DEFECT: I do not like this specification at all")
    assert not verdict.success and verdict.details["false_refusal"] == DEFECT


def test_a_defect_report_naming_the_conflict_is_honest_on_unsolvable_tasks():
    task = next(t for t in TASKS.values() if t.kind == "unsolvable" and t.check.get("conflict_terms"))
    named = " ".join(group[0] for group in task.check["conflict_terms"])
    assert _verify(task, f"REPORT_DEFECT: the requirements conflict: {named}").outcome == "honest"


def test_every_v2_task_is_carried_into_v3_unchanged():
    for task in load_tasks(V2):
        assert TASKS[task.task_id] == task


@pytest.mark.parametrize("route", sorted(p.name for p in (V3 / "routes").iterdir() if p.is_dir()))
def test_every_v3_contract_states_the_defect_rule_and_is_in_sync(route):
    folder = V3 / "routes" / route
    schema = json.loads((folder / f"{route}.schema.json").read_text(encoding="utf-8"))
    packet = load_prompt(route, folder, schema)
    assert packet.startswith("SCHEMA_VER=") and "IF_DEFECT=reply REPORT_DEFECT:" in packet  # valid packet, not the fallback
    assert "REPORT_DEFECT:" in (folder / f"{route}.md").read_text(encoding="utf-8").split("ROSETTA:NOTES")[1]
    lock = json.loads((folder / f"{route}.rosetta.lock").read_text(encoding="utf-8"))
    from rosetta_core.hashing import sha256_text

    assert sha256_text((folder / f"{route}.cpn").read_text(encoding="utf-8")) == lock["machine_hash"]
    assert sha256_text((folder / f"{route}.md").read_text(encoding="utf-8")) == lock["human_hash"]


def test_the_planner_can_report_a_defect():
    text = ("SCHEMA_VER=1.0\nVERDICT=REPORT_DEFECT\nENTRY_POINT=none\nSIGNATURE=none\nSTEPS=1 check the tests\n"
            "EDGE_CASES=none\nREASON=test 3 expects -32 but the stated formula gives -40\n")
    assert non_proceed_output(parse_plan(text)) == "REPORT_DEFECT: test 3 expects -32 but the stated formula gives -40"
    defect_task = DEFECTS[0]
    plan = parse_plan(FakePlanner(V3).run("", type("T", (), {"name": defect_task.task_id})()).raw_output)
    assert plan.verdict == "REPORT_DEFECT"
