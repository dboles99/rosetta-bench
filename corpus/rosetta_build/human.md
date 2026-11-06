<!-- ROSETTA:AUTO-GENERATED — edit fields via the embedded metadata or Rosetta CLI -->
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

<!-- ROSETTA:NOTES — hand-written, sync preserves this region -->
The compact packet is the normal LLM input; Markdown is a full fallback, not
additional context. Canonical fields, the packet, and the human view are all
tracked in the lock so direct edits to any representation cannot silently go
stale. Numeric packet values are recovered using the JSON Schema rather than
unsafe type guessing. Current size measurements are character-based token
estimates and must be replaced or supplemented with provider tokenizers before
claiming model-specific savings.
<!-- /ROSETTA:NOTES -->
