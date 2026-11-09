<!-- ROSETTA:AUTO-GENERATED — do not edit below this marker, edits will be overwritten by `rosetta sync` -->
<!-- ROSETTA:FIELDS {"DELIVERABLE": "answer-with-figures", "IF_DEFECT": "reply REPORT_DEFECT: <the defect and where it is>", "IF_PREMISE_FALSE": "reply PREMISE_REJECTED: <which premise is false and why>", "IF_UNSOLVABLE": "reply UNSOLVABLE: <one-line reason naming the conflicting or impossible requirements>", "OUTPUT_FORMAT": "brief-working,last-line:ANSWER: <value>", "ROUTE": "data_query", "SCOPE": "read-only,data-given-in-the-request"} -->
<!-- ROSETTA:SCHEMA_VER 1.0 -->
# Data Query
- DELIVERABLE: answer-with-figures
- IF_DEFECT: reply REPORT_DEFECT: <the defect and where it is>
- IF_PREMISE_FALSE: reply PREMISE_REJECTED: <which premise is false and why>
- IF_UNSOLVABLE: reply UNSOLVABLE: <one-line reason naming the conflicting or impossible requirements>
- OUTPUT_FORMAT: brief-working,last-line:ANSWER: <value>
- ROUTE: data_query
- SCOPE: read-only,data-given-in-the-request
<!-- /ROSETTA:AUTO-GENERATED -->

<!-- ROSETTA:NOTES — hand-written, sync never touches this region -->
Answer from the data given in the request only: show the figures briefly, then end with a final line
ANSWER: <value>. Never modify data. If the request cannot be satisfied as stated (contradictory or impossible requirements, or essential
information that does not exist and cannot be supplied), reply with no code and a single line UNSOLVABLE:
followed by a one-line reason naming the conflicting or impossible requirements. If the request rests on a
premise that is false (for example a bug the shown code does not have), reply with no code and a single line
PREMISE_REJECTED: followed by which premise is false and why.
- If the request's own specification, examples or tests contain a mistake, reply with no code and a single
  line REPORT_DEFECT: followed by the defect and where it is, instead of working around it.
<!-- /ROSETTA:NOTES -->
