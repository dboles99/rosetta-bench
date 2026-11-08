import pytest

from rosetta_bench.scoring.constraints import check_constraints, task_success


def _passed(output, constraint) -> bool:
    return check_constraints(output, [constraint])[0].passed


def test_must_include_passes_when_the_text_is_present():
    assert _passed("explains CONFLICT_POLICY", {"type": "must_include", "value": "CONFLICT_POLICY"})


def test_must_include_is_case_sensitive_by_default():
    assert not _passed("explains conflict_policy", {"type": "must_include", "value": "CONFLICT_POLICY"})
    assert _passed("explains conflict_policy", {"type": "must_include", "value": "CONFLICT_POLICY", "ignore_case": True})


def test_must_not_include():
    assert not _passed("the lock tracks the fields store", {"type": "must_not_include", "value": "tracks the fields store"})


def test_bullet_count_counts_dash_star_and_numbered_items():
    output = "Intro line\n- one\n* two\n3. three\n"
    assert _passed(output, {"type": "bullet_count", "equals": 3})
    assert not _passed(output, {"type": "bullet_count", "equals": 2})


def test_regex():
    assert _passed("SCHEMA_VER=1.0", {"type": "regex", "pattern": r"SCHEMA_VER=\d+\.\d+"})


def test_unknown_constraint_type_is_a_configuration_error():
    with pytest.raises(ValueError):
        check_constraints("x", [{"type": "vibes"}])


def test_results_name_each_constraint():
    results = check_constraints("x", [{"type": "must_include", "value": "x", "name": "mentions_x"}])
    assert results[0].name == "mentions_x"


def test_task_success_requires_every_constraint():
    passing = check_constraints("A B", [{"type": "must_include", "value": "A"}, {"type": "must_include", "value": "B"}])
    failing = check_constraints("A", [{"type": "must_include", "value": "A"}, {"type": "must_include", "value": "B"}])
    assert task_success(passing) is True
    assert task_success(failing) is False
    assert task_success([]) is None
