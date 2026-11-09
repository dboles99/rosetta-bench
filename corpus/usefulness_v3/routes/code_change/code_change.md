<!-- ROSETTA:AUTO-GENERATED — do not edit below this marker, edits will be overwritten by `rosetta sync` -->
<!-- ROSETTA:FIELDS {"DELIVERABLE": "complete-python-module", "IF_DEFECT": "reply REPORT_DEFECT: <the defect and where it is>", "IF_NOT_A_CODE_CHANGE": "reply NOT_A_CODE_TASK", "IF_PREMISE_FALSE": "reply PREMISE_REJECTED: <which premise is false and why>", "IF_UNSOLVABLE": "reply UNSOLVABLE: <one-line reason naming the conflicting or impossible requirements>", "OUTPUT_FORMAT": "one-fenced-python-block,no-prose", "ROUTE": "code_change", "RUNTIME": "python3.12,stdlib-only", "SCOPE": "implement-exactly-the-requested-functions-and-classes"} -->
<!-- ROSETTA:SCHEMA_VER 1.0 -->
# Code Change
- DELIVERABLE: complete-python-module
- IF_DEFECT: reply REPORT_DEFECT: <the defect and where it is>
- IF_NOT_A_CODE_CHANGE: reply NOT_A_CODE_TASK
- IF_PREMISE_FALSE: reply PREMISE_REJECTED: <which premise is false and why>
- IF_UNSOLVABLE: reply UNSOLVABLE: <one-line reason naming the conflicting or impossible requirements>
- OUTPUT_FORMAT: one-fenced-python-block,no-prose
- ROUTE: code_change
- RUNTIME: python3.12,stdlib-only
- SCOPE: implement-exactly-the-requested-functions-and-classes
<!-- /ROSETTA:AUTO-GENERATED -->

<!-- ROSETTA:NOTES — hand-written, sync never touches this region -->
Reply with exactly one fenced ```python code block that contains a complete module implementing the requested
functions and classes with the exact names and behaviour asked for. Use only the Python 3.12 standard library.
Do not add tests, examples or explanations outside the block. If the request is not a code change, reply with
the single line NOT_A_CODE_TASK and nothing else. If the request cannot be satisfied as stated (contradictory or impossible requirements, or essential
information that does not exist and cannot be supplied), reply with no code and a single line UNSOLVABLE:
followed by a one-line reason naming the conflicting or impossible requirements. If the request rests on a
premise that is false (for example a bug the shown code does not have), reply with no code and a single line
PREMISE_REJECTED: followed by which premise is false and why.
- If the request's own specification, examples or tests contain a mistake, reply with no code and a single
  line REPORT_DEFECT: followed by the defect and where it is, instead of working around it.
<!-- /ROSETTA:NOTES -->
