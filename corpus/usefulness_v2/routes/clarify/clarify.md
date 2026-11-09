<!-- ROSETTA:AUTO-GENERATED — do not edit below this marker, edits will be overwritten by `rosetta sync` -->
<!-- ROSETTA:FIELDS {"DELIVERABLE": "clarifying-questions", "IF_PREMISE_FALSE": "reply PREMISE_REJECTED: <which premise is false and why>", "IF_UNSOLVABLE": "reply UNSOLVABLE: <one-line reason naming the conflicting or impossible requirements>", "OUTPUT_FORMAT": "at-most-three-questions", "ROUTE": "clarify", "SCOPE": "no-implementation"} -->
<!-- ROSETTA:SCHEMA_VER 1.0 -->
# Clarify
- DELIVERABLE: clarifying-questions
- IF_PREMISE_FALSE: reply PREMISE_REJECTED: <which premise is false and why>
- IF_UNSOLVABLE: reply UNSOLVABLE: <one-line reason naming the conflicting or impossible requirements>
- OUTPUT_FORMAT: at-most-three-questions
- ROUTE: clarify
- SCOPE: no-implementation
<!-- /ROSETTA:AUTO-GENERATED -->

<!-- ROSETTA:NOTES — hand-written, sync never touches this region -->
Ask at most three short questions that would let the request be carried out. Do not attempt the work and do
not write code. If the request cannot be satisfied as stated (contradictory or impossible requirements, or essential
information that does not exist and cannot be supplied), reply with no code and a single line UNSOLVABLE:
followed by a one-line reason naming the conflicting or impossible requirements. If the request rests on a
premise that is false (for example a bug the shown code does not have), reply with no code and a single line
PREMISE_REJECTED: followed by which premise is false and why.
<!-- /ROSETTA:NOTES -->
