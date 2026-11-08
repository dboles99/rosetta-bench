<!-- ROSETTA:AUTO-GENERATED — do not edit below this marker, edits will be overwritten by `rosetta sync` -->
<!-- ROSETTA:FIELDS {"CACHE_STABILITY": "canonical-key-order,LF,fixed-floats", "CONFLICT_POLICY": "explicit,no-auto-merge", "FIELD_VALUE_TYPES": "str,int,float", "NORMAL_PROMPT_VIEW": "CPN", "RUNTIME_FALLBACK": "human-markdown", "TASK": "ROSETTA_BUILD"} -->
<!-- ROSETTA:SCHEMA_VER 1.0 -->
# Rosetta Build
- CACHE_STABILITY: canonical-key-order,LF,fixed-floats
- CONFLICT_POLICY: explicit,no-auto-merge
- FIELD_VALUE_TYPES: str,int,float
- NORMAL_PROMPT_VIEW: CPN
- RUNTIME_FALLBACK: human-markdown
- TASK: ROSETTA_BUILD
<!-- /ROSETTA:AUTO-GENERATED -->

<!-- ROSETTA:NOTES — hand-written, sync never touches this region -->
The compact packet is the normal LLM input; Markdown is a full fallback, not
additional context. The lock file records hashes of the packet and of this
human view, so a direct edit to either view is detected; an edit made only to
the canonical fields file is not detected by sync. Packet values are always
parsed as strings, so numeric values are recovered using the JSON Schema's
declared types rather than unsafe type guessing. Current size measurements are
character-based token estimates and must be replaced or supplemented with
provider tokenizers before claiming model-specific savings.
<!-- /ROSETTA:NOTES -->
