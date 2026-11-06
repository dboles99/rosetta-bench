# Rosetta-bench: human vs. machine-readable prompt benchmark

**Status:** Design notes for v1.
**Date:** 2026-07-13

## Problem

Rosetta (the dual-representation prompt/metadata system, the `rosetta-core` package) claims a compact machine-readable packet (`.cpn`) is faster and at least as effective for an LLM/tool to consume as the full human-readable document (`.md`) it's paired with. That claim has never been measured. Before recommending Rosetta's compact format as the default for real integrations, we want evidence: does the compact form actually read faster, cost fewer tokens, and produce equally (or more) correct/complete results than the verbose form, across more than one model/tool?

## Goals

- Measure, not assume: run the same underlying task/question against both prompt formats (human `.md` vs. machine `.cpn`) across multiple tools, and record the difference.
- Cover two distinct questions, not one conflated metric: can a tool understand the prompt (comprehension), and does understanding translate into a correct completed task (task completion).
- Cover real, already-existing prompt pairs first (Rosetta's own dogfooded artifact), before investing in a synthetic/independent corpus.
- Produce a durable, importable results artifact (spreadsheet), not just terminal output.
- Keep the tool list to what's actually automatable via an API; treat interactive dev-tool comparisons as a separate, later, informal exercise.

## Non-goals

- Not a live dashboard or a shared/multi-user product, a small research tool.
- Not an automated harness for Cline or Codex (no stable scriptable API for either); excluded from this repo's scope.
- Not a claim-generating tool, this produces data and an LLM-judged quality score; drawing conclusions from the data is a separate, later step done by hand.
- Not a general-purpose prompt-eval framework, scoped specifically to the human-vs-machine-readable-format comparison.

## Test corpus

**Stage 1 (this spec):** Rosetta's own dogfooded example (`rosetta_build`: `fields.json` → `.cpn` + `.md`) plus 1-2 additional PacketSpec artifacts created for variety (more fields, a richer notes region), generated the same way via the `rosetta` CLI already built in the `rosetta` repo.

**Stage 2 (future, out of scope for this spec):** an independent prompt set not derived from Rosetta's own design, to check Stage 1 results aren't an artifact of Rosetta's specific choices (e.g. the JSON-comment round-trip design). Noted here as a deliberate follow-up, not designed now.

Each corpus case lives in its own folder under `corpus/<case_name>/` containing:
- `human.md`, the human-readable view (copied from the Rosetta artifact)
- `machine.cpn`, the machine-readable view (copied from the Rosetta artifact)
- `answer_key.yaml`, for Suite A: a fixed list of questions and their correct answers, derived from the underlying fields
- `task_spec.yaml`, for Suite B: one concrete task description, its acceptance criteria, and (where applicable) a reference/expected output for the judge to compare against

## Test suites

### Suite A, Comprehension

The tool is given one prompt format (human or machine) and asked a fixed battery of factual questions about its content (e.g. "What is the value of `ID_THRESHOLD`?"). The same questions are asked regardless of format; only the source prompt changes. Scored against `answer_key.yaml` (exact-match where possible, LLM-judged semantic match otherwise). This isolates raw readability from any task-execution ability.

### Suite B, Task completion

The tool is given one prompt format and one concrete task from `task_spec.yaml` (e.g., "write a function that validates a value against this policy," or "summarize this for a new teammate and flag any conflicts"). Measures wall-clock time, tokens, and an LLM-judged quality score against the rubric below. This isolates whether comprehension differences actually change task outcomes.

**Azure Translation asymmetry:** Azure Translation doesn't accept arbitrary task instructions, it translates text. Its runner is scoped to Suite A only, operationalized as: translate the prompt to a second language and back, then answer the same comprehension questions against the round-tripped text, to see whether meaning survives the round trip differently for the two formats. It does not participate in Suite B.

## Schema

One CSV row per trial (`storage/trials.csv`, canonical source of truth):

```
trial_id, timestamp, tool, model, prompt_id, prompt_format (HUMAN|MACHINE),
suite (COMPREHENSION|TASK_COMPLETION), tokens_in, tokens_out, latency_ms,
turns, task_success (bool), comprehension_accuracy (0-1, Suite A only),
quality_score (1-5, Suite B only), judge_justification, cost_usd, raw_output
```

`cost_usd` is computed from each tool's published per-token pricing (a small static lookup table in the harness, not fetched live).

## Rubric (LLM-as-judge, 1-5 each, Suite B only)

1. **Correctness**, did the output fulfill the task
2. **Completeness**, did it address every part of the prompt/task
3. **Faithfulness to constraints**, did it actually follow the rules/format embedded in the prompt (not just gesture at them)
4. **Clarity/actionability** of the output

The judge is a single Claude API call per trial, given: the task spec, the rubric, the model's raw output, and (if present) the reference output from `task_spec.yaml`. It returns a 1-5 score per dimension plus a short justification, stored as `quality_score` (mean of the four) and `judge_justification` (the raw per-dimension breakdown).

## Architecture

This is the layout as first designed. The implemented layout is flatter (`judge.py`, `storage.py` and `export_xlsx.py` are single modules under `src/rosetta_bench/`), and `bench run` is not wired to live services; see the README.

```
rosetta-bench/
  corpus/<case_name>/           # human.md, machine.cpn, answer_key.yaml, task_spec.yaml
  runners/
    base.py                     # Runner.run(prompt_text, task) -> RunResult
    claude_runner.py            # Anthropic API
    azure_openai_runner.py       # Azure OpenAI API
    azure_translation_runner.py  # Azure Translator API, Suite A only
    ollama_runner.py             # local Ollama HTTP API
  judge/
    llm_judge.py                 # scores a trial's raw_output against task_spec + rubric
  harness.py                     # orchestrates: for each tool x prompt x format x suite -> runner -> (judge) -> trial row
  storage/
    trials.csv                   # canonical, append-only source of truth (gitignored: run output, not source)
  export/
    to_xlsx.py                   # CSV -> .xlsx, raw-data sheet + summary/pivot sheet
    to_sheets.py                  # CSV -> Google Sheets via API (optional, needs credentials)
  cli.py                          # bench run / bench export xlsx / bench export sheets
  .env.example                    # ANTHROPIC_API_KEY, AZURE_OPENAI_*, AZURE_TRANSLATOR_*, OLLAMA_HOST
```

**Runner interface:** `Runner.run(prompt_text: str, task: Task | None) -> RunResult` (`RunResult` carries raw output, tokens, latency, turn count). Each tool is one adapter file implementing this interface, so adding a fifth tool later is additive, not a harness rewrite.

**Export:** `trials.csv` is the single source of truth; `.xlsx` and Google Sheets are both generated FROM it, never the other way around, so there's never a question of which is authoritative.

**Credentials:** all via environment variables (`.env`, gitignored), documented in `.env.example`, never committed.

## Open questions (deferred, not blocking Stage 1)

- Exact per-tool pricing table for `cost_usd`, needs current published rates at implementation time, not guessed now.
- Whether `comprehension_accuracy` uses exact-match or LLM-judged semantic match by default, likely both, exact-match first with LLM-judge as fallback for free-text answers, to be finalized during implementation planning.
- Stage 2's independent prompt corpus, explicitly deferred, not designed here.
