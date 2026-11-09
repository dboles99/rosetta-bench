<!-- ROSETTA:AUTO-GENERATED — do not edit below this marker, edits will be overwritten by `rosetta sync` -->
<!-- ROSETTA:FIELDS {"DELIVERABLE": "revised-documentation-text", "IF_DEFECT": "reply REPORT_DEFECT: <the defect and where it is>", "IF_NOT_DOCS": "reply NOT_A_DOCS_TASK", "IF_PREMISE_FALSE": "reply PREMISE_REJECTED: <which premise is false and why>", "IF_UNSOLVABLE": "reply UNSOLVABLE: <one-line reason naming the conflicting or impossible requirements>", "OUTPUT_FORMAT": "markdown-prose,no-code", "ROUTE": "docs_edit", "SCOPE": "documentation-only"} -->
<!-- ROSETTA:SCHEMA_VER 1.0 -->
# Docs Edit
- DELIVERABLE: revised-documentation-text
- IF_DEFECT: reply REPORT_DEFECT: <the defect and where it is>
- IF_NOT_DOCS: reply NOT_A_DOCS_TASK
- IF_PREMISE_FALSE: reply PREMISE_REJECTED: <which premise is false and why>
- IF_UNSOLVABLE: reply UNSOLVABLE: <one-line reason naming the conflicting or impossible requirements>
- OUTPUT_FORMAT: markdown-prose,no-code
- ROUTE: docs_edit
- SCOPE: documentation-only
<!-- /ROSETTA:AUTO-GENERATED -->

<!-- ROSETTA:NOTES — hand-written, sync never touches this region -->
Reply with the revised documentation text only, in Markdown. Do not write or change code. If the request is
not a documentation edit, reply with the single line NOT_A_DOCS_TASK. If the request cannot be satisfied as stated (contradictory or impossible requirements, or essential
information that does not exist and cannot be supplied), reply with no code and a single line UNSOLVABLE:
followed by a one-line reason naming the conflicting or impossible requirements. If the request rests on a
premise that is false (for example a bug the shown code does not have), reply with no code and a single line
PREMISE_REJECTED: followed by which premise is false and why.
- If the request's own specification, examples or tests contain a mistake, reply with no code and a single
  line REPORT_DEFECT: followed by the defect and where it is, instead of working around it.
<!-- /ROSETTA:NOTES -->
