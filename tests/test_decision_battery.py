import pytest

pytest.importorskip("rosetta_core.decision", reason="decision tests need rosetta-core installed")

from rosetta_core.decision import Primitive

from rosetta_bench.decision.battery import intake_battery

ROUTES = [{"id": "code_change", "description": "Change code"}, {"id": "clarify", "description": "Ask for details"}]


def test_noul_questions_carry_no_criteria_so_every_provider_accepts_them():
    # clef (via Ollama, 2026-11-09) rejected noul criteria keyed "yes"/"no" with HTTP 400;
    # jevmodel accepted them. The portable form puts the yes/no meaning in the instructions.
    for question in intake_battery(ROUTES).questions:
        if question.primitive is Primitive.NOUL:
            assert question.criteria is None, question.qid


def test_route_fits_instructions_define_both_answers():
    route_fits = intake_battery(ROUTES).get("route_fits")
    assert "Answer yes" in route_fits.instructions
    assert "answer no" in route_fits.instructions


def test_portable_battery_has_a_new_version():
    qset = intake_battery(ROUTES)
    assert qset.version == "1.1"
    assert qset.get("route_fits").version == "1.1"
