"""Reason-first pipeline: reasoning -> prompt -> Rosetta -> execution.

1. Plan: one call with reasoning on. The planner writes no code, only KEY=VALUE lines.
2. Rosetta: the plan is parsed and re-serialized by rosetta-core into a canonical, schema-validated
   PacketSpec packet, so equivalent plans are byte-identical and cacheable by digest.
3. Execute: the route contract (.cpn) plus the plan packet plus the request, with reasoning off.
   A refusing verdict (UNSOLVABLE, PREMISE_REJECTED, REPORT_DEFECT) is answered with the contract's marker and
   no execution. A hand-off verdict (NOT_A_CODE_TASK, NEEDS_CLARIFICATION) is executed with the route contract
   and no plan: answering a non-code request or asking for missing details is the contract's job.
   Plan schema 1.1 (2026-11-09): live run 20 answered every non-code task with the bare NOT_A_CODE_TASK
   marker and had no way to ask for missing details; 1.0 plans are not comparable.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from rosetta_core.cpn import serialize_packet
from rosetta_core.decision.contracts import canonical_json
from rosetta_core.hashing import sha256_text
from rosetta_core.schema import SchemaValidationError, validate_fields

PLAN_SCHEMA_VER = "1.1"
REFUSING_VERDICTS = ("UNSOLVABLE", "PREMISE_REJECTED", "REPORT_DEFECT")
HANDOFF_VERDICTS = ("NOT_A_CODE_TASK", "NEEDS_CLARIFICATION")
VERDICTS = ("PROCEED", *REFUSING_VERDICTS, *HANDOFF_VERDICTS)
PLAN_FIELDS = ("VERDICT", "ENTRY_POINT", "SIGNATURE", "STEPS", "EDGE_CASES", "REASON")
PLAN_SCHEMA = {
    "type": "object",
    "required": ["SCHEMA_VER", *PLAN_FIELDS],
    "properties": {
        "SCHEMA_VER": {"type": "string", "pattern": r"^\d+\.\d+$"},
        "VERDICT": {"type": "string", "enum": list(VERDICTS)},
        "ENTRY_POINT": {"type": "string", "maxLength": 120},
        "SIGNATURE": {"type": "string", "maxLength": 400},
        "STEPS": {"type": "string", "minLength": 1, "maxLength": 2000},
        "EDGE_CASES": {"type": "string", "maxLength": 1500},
        "REASON": {"type": "string", "minLength": 1, "maxLength": 600},
    },
}
PLANNER_PROMPT = """You are the planning stage. Think the request through, then reply with ONLY these lines, one per line:
SCHEMA_VER=1.1
VERDICT=<PROCEED | UNSOLVABLE | PREMISE_REJECTED | REPORT_DEFECT | NOT_A_CODE_TASK | NEEDS_CLARIFICATION>
ENTRY_POINT=<function or class name to implement, or none>
SIGNATURE=<Python signature, or none>
STEPS=<numbered steps separated by ' | '>
EDGE_CASES=<edge cases separated by ' | ', or none>
REASON=<one line: why, required for any verdict other than PROCEED; otherwise none>
Use UNSOLVABLE when the requirements contradict each other or cannot all be met, PREMISE_REJECTED when the request
relies on something the supplied evidence shows is false, REPORT_DEFECT when the request's own specification,
examples or tests contain a mistake, NOT_A_CODE_TASK when the request asks for something other than code (an
answer, a document edit, a data query, a review), NEEDS_CLARIFICATION when details the work needs are missing
but could be supplied. NOT_A_CODE_TASK and NEEDS_CLARIFICATION hand the request on to be answered normally.
Do not write code. Keep every value on a single line.
"""
_LINE = re.compile(r"^\s*([A-Z_]+)\s*=\s*(.*?)\s*$")


class PlanError(ValueError):
    pass


@dataclass(frozen=True)
class Plan:
    fields: dict
    packet: str
    digest: str

    @property
    def verdict(self) -> str:
        return self.fields["VERDICT"]


def parse_plan(text: str) -> Plan:
    """Turn planner output into a canonical, validated Rosetta packet. Unknown keys are dropped."""
    values: dict[str, str] = {}
    for line in (text or "").replace("\r\n", "\n").split("\n"):
        match = _LINE.match(line.strip("` "))
        if match and (match.group(1) in PLAN_FIELDS or match.group(1) == "SCHEMA_VER") and match.group(1) not in values:
            values[match.group(1)] = match.group(2)
    schema_ver = values.pop("SCHEMA_VER", PLAN_SCHEMA_VER)
    try:
        validate_fields({**values, "SCHEMA_VER": schema_ver}, PLAN_SCHEMA)
    except SchemaValidationError as exc:
        raise PlanError(f"invalid plan: {exc}") from None
    if values["VERDICT"] != "PROCEED" and values["REASON"].strip().lower() in ("", "none"):
        raise PlanError(f"verdict {values['VERDICT']} needs a reason")
    packet = serialize_packet(schema_ver, values)
    return Plan(fields=values, packet=packet, digest=sha256_text(packet))


def execution_prompt(contract: str, plan: Plan, request_text: str) -> str:
    return f"{contract.rstrip()}\n\nPLAN (Rosetta packet; follow it):\n{plan.packet}\nRequest:\n{request_text}\n"


def non_proceed_output(plan: Plan) -> str:
    if plan.verdict == "NOT_A_CODE_TASK":
        return "NOT_A_CODE_TASK"
    return f"{plan.verdict}: {plan.fields['REASON']}"


def _normalise(text: str) -> str:
    return unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))


def plan_cache_key(request_text: str, *, model: str, sample: int) -> str:
    """Same request (after Rosetta canonicalisation), planner prompt, model and sample index -> same plan.
    The sample index keeps independent samples independent in experiments."""
    return sha256_text(canonical_json({"request": _normalise(request_text), "planner": sha256_text(PLANNER_PROMPT),
                                       "model": model, "sample": sample, "plan_schema": PLAN_SCHEMA_VER}))
