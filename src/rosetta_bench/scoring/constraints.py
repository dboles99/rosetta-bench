"""Exact requirement checks declared in a case's task_spec.yaml under `constraints`.

Supported types: must_include, must_not_include (optional ignore_case), regex
(pattern), bullet_count (equals). An unknown type is a configuration error.
"""
import re
from dataclasses import dataclass

_BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+\S")


@dataclass(frozen=True)
class ConstraintResult:
    name: str
    passed: bool
    detail: str = ""


def _contains(output: str, value: str, ignore_case: bool) -> bool:
    if ignore_case:
        return value.casefold() in output.casefold()
    return value in output


def _check(output: str, constraint: dict) -> tuple[bool, str]:
    kind = constraint.get("type")
    if kind == "must_include":
        return _contains(output, constraint["value"], constraint.get("ignore_case", False)), ""
    if kind == "must_not_include":
        return not _contains(output, constraint["value"], constraint.get("ignore_case", False)), ""
    if kind == "regex":
        return re.search(constraint["pattern"], output, flags=re.MULTILINE) is not None, ""
    if kind == "bullet_count":
        count = sum(1 for line in output.splitlines() if _BULLET.match(line))
        return count == constraint["equals"], f"found {count}"
    raise ValueError(f"unknown constraint type: {kind!r}")


def check_constraints(output: str, constraints: list[dict]) -> list[ConstraintResult]:
    results = []
    for constraint in constraints:
        passed, detail = _check(output, constraint)
        label = constraint.get("value", constraint.get("pattern", constraint.get("equals", "")))
        name = constraint.get("name") or f"{constraint['type']}:{label}"
        results.append(ConstraintResult(name=name, passed=passed, detail=detail))
    return results


def task_success(results: list[ConstraintResult]) -> bool | None:
    if not results:
        return None
    return all(result.passed for result in results)
