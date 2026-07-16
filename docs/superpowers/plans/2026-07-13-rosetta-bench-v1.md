# Rosetta-bench V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `rosetta-bench`, a Python package that runs the same comprehension/task-completion trials against Claude, Azure OpenAI, Azure Translation, and Ollama, in both the human-readable and machine-readable formats of a Rosetta prompt pair, and exports the results to CSV/xlsx/Google Sheets.

**Architecture:** A `Runner` protocol (`run(prompt_text, task) -> RunResult`) is implemented once per tool; each concrete runner takes an injected, protocol-typed API client so the runner's own logic (prompt assembly, timing, result shaping) is unit-testable without live network calls — only the thin SDK/HTTP adapter classes touch a real network, and those are not exercised by the automated test suite. `harness.py` orchestrates: for each (tool, prompt_format, suite) combination, call the runner, optionally call the judge, and append one `Trial` row to `storage/trials.csv` (the canonical source of truth). `export_xlsx.py`/`export_sheets.py` both read from that CSV; neither writes back to it.

**Tech Stack:** Python 3.11+, `pyyaml` (corpus files), `openpyxl` (.xlsx export), `gspread` + `google-auth` (Google Sheets export), `anthropic` (Claude SDK), `pytest`.

## Global Constraints

- Python 3.11+ only.
- All file I/O uses `encoding="utf-8"` explicitly.
- No automated test makes a real network call. Every runner's core logic is tested via an injected fake/protocol-typed client; only the thin concrete SDK/HTTP adapter classes are excluded from test coverage (documented as such, not silently skipped).
- `storage/trials.csv` is the single source of truth; `export_xlsx.py` and `export_sheets.py` only ever read from it, never write to it.
- Credentials (`ANTHROPIC_API_KEY`, `AZURE_OPENAI_*`, `AZURE_TRANSLATOR_*`, `OLLAMA_HOST`, Google service-account path) are read from environment variables only, documented in `.env.example`, never committed or hardcoded.
- Azure Translation only participates in Suite A (comprehension), never Suite B (task completion) — per the spec's documented asymmetry.

---

## File Structure

```
rosetta-bench/
  pyproject.toml                          # Task 1
  .gitignore                              # Task 1
  .env.example                            # Task 1
  src/rosetta_bench/
    __init__.py                           # Task 1
    models.py                             # Task 2
    pricing.py                            # Task 3
    corpus.py                             # Task 4
    judge.py                              # Task 5
    runners/
      __init__.py                         # Task 6
      base.py                             # Task 6
      claude_runner.py                    # Task 7
      azure_openai_runner.py              # Task 8
      ollama_runner.py                    # Task 9
      azure_translation_runner.py         # Task 10
    storage.py                            # Task 11
    harness.py                            # Task 12
    export_xlsx.py                        # Task 13
    export_sheets.py                      # Task 14
    cli.py                                # Task 15
  corpus/
    rosetta_build/
      human.md, machine.cpn, answer_key.yaml, task_spec.yaml   # Task 16
  tests/
    test_models.py                        # Task 2
    test_pricing.py                       # Task 3
    test_corpus.py                        # Task 4
    test_judge.py                         # Task 5
    test_runners_base.py                  # Task 6
    test_claude_runner.py                 # Task 7
    test_azure_openai_runner.py           # Task 8
    test_ollama_runner.py                 # Task 9
    test_azure_translation_runner.py      # Task 10
    test_storage.py                       # Task 11
    test_harness.py                       # Task 12
    test_export_xlsx.py                   # Task 13
    test_export_sheets.py                 # Task 14
    test_cli.py                           # Task 15
    test_end_to_end.py                    # Task 17
```

---

### Task 1: Project scaffold

**Suggested tool:** Cline (fast, low-risk project scaffolding).

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `src/rosetta_bench/__init__.py`

**Interfaces:**
- Produces: an installable package `rosetta_bench` importable from `tests/`.

- [x] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "rosetta-bench"
version = "0.1.0"
description = "Human-readable vs. machine-readable prompt benchmark for Rosetta"
requires-python = ">=3.11"
dependencies = [
    "pyyaml>=6.0",
    "openpyxl>=3.1",
    "gspread>=6.0",
    "google-auth>=2.29",
    "anthropic>=0.34",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[project.scripts]
bench = "rosetta_bench.cli:main"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

- [x] **Step 2: Create `.gitignore`**

```
.venv/
__pycache__/
*.pyc
.pytest_cache/
storage/trials.csv
.env
*.egg-info/
```

- [x] **Step 3: Create `.env.example`**

```
ANTHROPIC_API_KEY=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_DEPLOYMENT=
AZURE_TRANSLATOR_API_KEY=
AZURE_TRANSLATOR_ENDPOINT=
AZURE_TRANSLATOR_REGION=
OLLAMA_HOST=http://localhost:11434
GOOGLE_SERVICE_ACCOUNT_JSON=
```

- [x] **Step 4: Create the empty package `src/rosetta_bench/__init__.py`**

```python
"""Rosetta-bench: human-readable vs. machine-readable prompt benchmark."""
```

- [x] **Step 5: Install in editable/dev mode and verify pytest collects zero tests without error**

Run: `pip install -e ".[dev]"`
Then run: `pytest -q`
Expected: `no tests ran` (exit code 5) or `0 items` — no import errors.

- [x] **Step 6: Commit**

```bash
git add pyproject.toml .gitignore .env.example src/rosetta_bench/__init__.py
git commit -m "Scaffold rosetta-bench package"
```

---

### Task 2: Data models

**Suggested tool:** Codex (small, pure dataclasses, clear contract).

**Files:**
- Create: `src/rosetta_bench/models.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Produces: `Task(name: str, instructions: str, reference_output: str | None = None)`, `RunResult(raw_output: str, tokens_in: int, tokens_out: int, latency_ms: float, turns: int = 1)`, `Trial` (the full CSV-row schema from the spec, with `.to_row() -> dict` returning columns in canonical order). Used by every later task.

- [x] **Step 1: Write the failing test**

```python
# tests/test_models.py
from rosetta_bench.models import Task, RunResult, Trial

CANONICAL_COLUMNS = [
    "trial_id", "timestamp", "tool", "model", "prompt_id", "prompt_format",
    "suite", "tokens_in", "tokens_out", "latency_ms", "turns", "task_success",
    "comprehension_accuracy", "quality_score", "judge_justification",
    "cost_usd", "raw_output",
]


def test_task_holds_instructions_and_optional_reference():
    task = Task(name="validate", instructions="do the thing")
    assert task.reference_output is None
    task2 = Task(name="validate", instructions="do the thing", reference_output="expected")
    assert task2.reference_output == "expected"


def test_run_result_defaults_turns_to_one():
    result = RunResult(raw_output="hi", tokens_in=10, tokens_out=5, latency_ms=123.4)
    assert result.turns == 1


def test_trial_to_row_has_canonical_columns_in_order():
    trial = Trial(
        trial_id="t1", timestamp="2026-07-13T00:00:00Z", tool="CLAUDE", model="claude-sonnet-5",
        prompt_id="rosetta_build", prompt_format="MACHINE", suite="COMPREHENSION",
        tokens_in=100, tokens_out=20, latency_ms=456.0, turns=1, task_success=None,
        comprehension_accuracy=0.9, quality_score=None, judge_justification="",
        cost_usd=0.001, raw_output="the answer",
    )
    row = trial.to_row()
    assert list(row.keys()) == CANONICAL_COLUMNS
    assert row["tool"] == "CLAUDE"
    assert row["comprehension_accuracy"] == 0.9
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'rosetta_bench.models'`

- [x] **Step 3: Write minimal implementation**

```python
# src/rosetta_bench/models.py
from dataclasses import dataclass


@dataclass
class Task:
    name: str
    instructions: str
    reference_output: str | None = None


@dataclass
class RunResult:
    raw_output: str
    tokens_in: int
    tokens_out: int
    latency_ms: float
    turns: int = 1


@dataclass
class Trial:
    trial_id: str
    timestamp: str
    tool: str
    model: str
    prompt_id: str
    prompt_format: str
    suite: str
    tokens_in: int
    tokens_out: int
    latency_ms: float
    turns: int
    task_success: bool | None
    comprehension_accuracy: float | None
    quality_score: float | None
    judge_justification: str
    cost_usd: float
    raw_output: str

    def to_row(self) -> dict:
        return {
            "trial_id": self.trial_id,
            "timestamp": self.timestamp,
            "tool": self.tool,
            "model": self.model,
            "prompt_id": self.prompt_id,
            "prompt_format": self.prompt_format,
            "suite": self.suite,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "latency_ms": self.latency_ms,
            "turns": self.turns,
            "task_success": self.task_success,
            "comprehension_accuracy": self.comprehension_accuracy,
            "quality_score": self.quality_score,
            "judge_justification": self.judge_justification,
            "cost_usd": self.cost_usd,
            "raw_output": self.raw_output,
        }
```

- [x] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py -v`
Expected: 3 passed

- [x] **Step 5: Commit**

```bash
git add src/rosetta_bench/models.py tests/test_models.py
git commit -m "Add Task/RunResult/Trial data models"
```

---

### Task 3: Pricing lookup

**Suggested tool:** Codex (small, pure, self-contained).

**Files:**
- Create: `src/rosetta_bench/pricing.py`
- Test: `tests/test_pricing.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `estimate_cost(tool: str, model: str, tokens_in: int, tokens_out: int) -> float`. Used by `harness.py` (Task 12).

- [x] **Step 1: Write the failing test**

```python
# tests/test_pricing.py
from rosetta_bench.pricing import estimate_cost


def test_known_tool_and_model_computes_cost():
    cost = estimate_cost("CLAUDE", "claude-sonnet-5", tokens_in=1000, tokens_out=1000)
    assert cost > 0


def test_unknown_tool_or_model_returns_zero():
    assert estimate_cost("UNKNOWN_TOOL", "unknown-model", tokens_in=1000, tokens_out=1000) == 0.0


def test_zero_tokens_costs_zero():
    assert estimate_cost("CLAUDE", "claude-sonnet-5", tokens_in=0, tokens_out=0) == 0.0


def test_ollama_local_model_is_free():
    assert estimate_cost("OLLAMA", "llama3", tokens_in=100000, tokens_out=100000) == 0.0
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pricing.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'rosetta_bench.pricing'`

- [x] **Step 3: Write minimal implementation**

```python
# src/rosetta_bench/pricing.py

# USD per 1,000 tokens: (input_price, output_price). Static snapshot, not live-fetched;
# update when tool pricing changes. Unlisted (tool, model) pairs cost 0.0.
PRICING_PER_1K_TOKENS: dict[tuple[str, str], tuple[float, float]] = {
    ("CLAUDE", "claude-sonnet-5"): (0.003, 0.015),
    ("AZURE_OPENAI", "gpt-4o"): (0.005, 0.015),
    ("OLLAMA", "llama3"): (0.0, 0.0),
}


def estimate_cost(tool: str, model: str, tokens_in: int, tokens_out: int) -> float:
    price_in, price_out = PRICING_PER_1K_TOKENS.get((tool, model), (0.0, 0.0))
    return (tokens_in / 1000) * price_in + (tokens_out / 1000) * price_out
```

- [x] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_pricing.py -v`
Expected: 4 passed

- [x] **Step 5: Commit**

```bash
git add src/rosetta_bench/pricing.py tests/test_pricing.py
git commit -m "Add per-token cost estimation"
```

---

### Task 4: Corpus loader

**Suggested tool:** Codex (straightforward file-reading logic).

**Files:**
- Create: `src/rosetta_bench/corpus.py`
- Test: `tests/test_corpus.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `Case(case_id: str, human_text: str, machine_text: str, answer_key: list[dict], task_spec: dict)` and `load_case(corpus_dir: Path, case_id: str) -> Case`. Used by `harness.py` (Task 12).

- [x] **Step 1: Write the failing test**

```python
# tests/test_corpus.py
from pathlib import Path
from rosetta_bench.corpus import load_case


def _write_case(corpus_dir: Path, case_id: str):
    case_dir = corpus_dir / case_id
    case_dir.mkdir(parents=True)
    (case_dir / "human.md").write_text("# Human doc\ncontent", encoding="utf-8")
    (case_dir / "machine.cpn").write_text("SCHEMA_VER=1.0\nTASK=X\n", encoding="utf-8")
    (case_dir / "answer_key.yaml").write_text(
        "- question: What is TASK?\n  answer: X\n", encoding="utf-8"
    )
    (case_dir / "task_spec.yaml").write_text(
        "name: validate\ninstructions: do the thing\nreference_output: null\n", encoding="utf-8"
    )


def test_load_case_reads_all_four_files(tmp_path: Path):
    _write_case(tmp_path, "example_case")
    case = load_case(tmp_path, "example_case")
    assert case.case_id == "example_case"
    assert "Human doc" in case.human_text
    assert "SCHEMA_VER=1.0" in case.machine_text
    assert case.answer_key == [{"question": "What is TASK?", "answer": "X"}]
    assert case.task_spec == {"name": "validate", "instructions": "do the thing", "reference_output": None}
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_corpus.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'rosetta_bench.corpus'`

- [x] **Step 3: Write minimal implementation**

```python
# src/rosetta_bench/corpus.py
import yaml
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Case:
    case_id: str
    human_text: str
    machine_text: str
    answer_key: list[dict]
    task_spec: dict


def load_case(corpus_dir: Path, case_id: str) -> Case:
    case_dir = corpus_dir / case_id
    human_text = (case_dir / "human.md").read_text(encoding="utf-8")
    machine_text = (case_dir / "machine.cpn").read_text(encoding="utf-8")
    answer_key = yaml.safe_load((case_dir / "answer_key.yaml").read_text(encoding="utf-8"))
    task_spec = yaml.safe_load((case_dir / "task_spec.yaml").read_text(encoding="utf-8"))
    return Case(
        case_id=case_id,
        human_text=human_text,
        machine_text=machine_text,
        answer_key=answer_key,
        task_spec=task_spec,
    )
```

- [x] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_corpus.py -v`
Expected: 1 passed

- [x] **Step 5: Commit**

```bash
git add src/rosetta_bench/corpus.py tests/test_corpus.py
git commit -m "Add corpus case loader"
```

---

### Task 5: LLM-as-judge

**Suggested tool:** Claude Code subagent (the rubric-parsing logic is correctness-critical — a silent misparse would corrupt every quality_score in the dataset).

**Files:**
- Create: `src/rosetta_bench/judge.py`
- Test: `tests/test_judge.py`

**Interfaces:**
- Consumes: nothing from earlier tasks (pure functions plus an injected `call_fn`).
- Produces: `JudgeResult(correctness: int, completeness: int, faithfulness: int, clarity: int, justification: str)` with a `.mean_score -> float` property, `build_judge_prompt(task_instructions: str, raw_output: str, reference_output: str | None) -> str`, `parse_judge_response(response_text: str) -> JudgeResult`, and `score_trial(task_instructions: str, raw_output: str, reference_output: str | None, call_fn: Callable[[str], str]) -> JudgeResult`. Used by `harness.py` (Task 12).

- [x] **Step 1: Write the failing test**

```python
# tests/test_judge.py
import pytest
from rosetta_bench.judge import build_judge_prompt, parse_judge_response, score_trial, JudgeResult

CANNED_RESPONSE = (
    "CORRECTNESS: 4\n"
    "COMPLETENESS: 5\n"
    "FAITHFULNESS: 3\n"
    "CLARITY: 4\n"
    "JUSTIFICATION: The output correctly addressed the task but missed one\n"
    "edge case mentioned in the constraints.\n"
)


def test_build_judge_prompt_includes_task_and_output():
    prompt = build_judge_prompt("do the thing", "here is my output", reference_output=None)
    assert "do the thing" in prompt
    assert "here is my output" in prompt


def test_build_judge_prompt_includes_reference_when_present():
    prompt = build_judge_prompt("do the thing", "output", reference_output="expected answer")
    assert "expected answer" in prompt


def test_parse_judge_response_extracts_all_scores_and_multiline_justification():
    result = parse_judge_response(CANNED_RESPONSE)
    assert result.correctness == 4
    assert result.completeness == 5
    assert result.faithfulness == 3
    assert result.clarity == 4
    assert "missed one" in result.justification
    assert "edge case" in result.justification


def test_judge_result_mean_score():
    result = JudgeResult(correctness=4, completeness=5, faithfulness=3, clarity=4, justification="")
    assert result.mean_score == 4.0


def test_score_trial_calls_call_fn_with_built_prompt_and_parses_result():
    captured_prompts = []

    def fake_call_fn(prompt: str) -> str:
        captured_prompts.append(prompt)
        return CANNED_RESPONSE

    result = score_trial("do the thing", "my output", None, fake_call_fn)
    assert result.correctness == 4
    assert len(captured_prompts) == 1
    assert "do the thing" in captured_prompts[0]


def test_parse_judge_response_raises_on_missing_field():
    with pytest.raises(KeyError):
        parse_judge_response("CORRECTNESS: 4\nJUSTIFICATION: incomplete response\n")
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_judge.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'rosetta_bench.judge'`

- [x] **Step 3: Write minimal implementation**

```python
# src/rosetta_bench/judge.py
from dataclasses import dataclass
from typing import Callable

JudgeCallFn = Callable[[str], str]

_SCORE_FIELDS = ("CORRECTNESS", "COMPLETENESS", "FAITHFULNESS", "CLARITY")


@dataclass
class JudgeResult:
    correctness: int
    completeness: int
    faithfulness: int
    clarity: int
    justification: str

    @property
    def mean_score(self) -> float:
        return (self.correctness + self.completeness + self.faithfulness + self.clarity) / 4


def build_judge_prompt(task_instructions: str, raw_output: str, reference_output: str | None) -> str:
    reference_block = f"\nReference/expected output:\n{reference_output}\n" if reference_output else ""
    return (
        "You are scoring an AI system's output against a rubric. Score each dimension 1-5.\n\n"
        f"Task instructions:\n{task_instructions}\n"
        f"{reference_block}\n"
        f"Output to score:\n{raw_output}\n\n"
        "Respond with exactly this format, one line each, justification may span multiple lines:\n"
        "CORRECTNESS: <1-5>\n"
        "COMPLETENESS: <1-5>\n"
        "FAITHFULNESS: <1-5>\n"
        "CLARITY: <1-5>\n"
        "JUSTIFICATION: <explanation>"
    )


def parse_judge_response(response_text: str) -> JudgeResult:
    scores: dict[str, int] = {}
    justification_lines: list[str] = []
    in_justification = False
    for line in response_text.splitlines():
        if line.startswith("JUSTIFICATION:"):
            in_justification = True
            justification_lines.append(line[len("JUSTIFICATION:"):].strip())
            continue
        if in_justification:
            if line.strip():
                justification_lines.append(line.strip())
            continue
        for field in _SCORE_FIELDS:
            if line.startswith(f"{field}:"):
                scores[field] = int(line[len(field) + 1:].strip())

    missing = [f for f in _SCORE_FIELDS if f not in scores]
    if missing:
        raise KeyError(f"judge response missing fields: {missing}")

    return JudgeResult(
        correctness=scores["CORRECTNESS"],
        completeness=scores["COMPLETENESS"],
        faithfulness=scores["FAITHFULNESS"],
        clarity=scores["CLARITY"],
        justification=" ".join(justification_lines).strip(),
    )


def score_trial(
    task_instructions: str,
    raw_output: str,
    reference_output: str | None,
    call_fn: JudgeCallFn,
) -> JudgeResult:
    prompt = build_judge_prompt(task_instructions, raw_output, reference_output)
    response_text = call_fn(prompt)
    return parse_judge_response(response_text)
```

- [x] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_judge.py -v`
Expected: 6 passed

- [x] **Step 5: Commit**

```bash
git add src/rosetta_bench/judge.py tests/test_judge.py
git commit -m "Add LLM-as-judge scoring"
```

---

### Task 6: Runner protocol

**Suggested tool:** Claude Code subagent (this interface is the contract every runner and the harness depend on — getting it right matters more than typing speed).

**Files:**
- Create: `src/rosetta_bench/runners/__init__.py`
- Create: `src/rosetta_bench/runners/base.py`
- Test: `tests/test_runners_base.py`

**Interfaces:**
- Consumes: `RunResult`, `Task` (Task 2).
- Produces: `Runner` (a `typing.Protocol` with `name: str`, `model: str`, and `run(self, prompt_text: str, task: Task | None) -> RunResult`). Used by every runner (Tasks 7-10) and `harness.py` (Task 12).

- [x] **Step 1: Write the failing test**

```python
# tests/test_runners_base.py
from rosetta_bench.models import RunResult, Task
from rosetta_bench.runners.base import Runner


class FakeRunner:
    name = "FAKE"
    model = "fake-model-v1"

    def run(self, prompt_text: str, task: Task | None) -> RunResult:
        return RunResult(raw_output=f"echo: {prompt_text}", tokens_in=1, tokens_out=1, latency_ms=0.1)


def test_fake_runner_satisfies_runner_protocol():
    runner: Runner = FakeRunner()
    result = runner.run("hello", None)
    assert result.raw_output == "echo: hello"


def test_runner_protocol_is_structural_not_nominal():
    # FakeRunner never inherits from Runner -- conformance is structural (duck-typed),
    # verified via isinstance() at runtime because Runner is @runtime_checkable.
    # issubclass() is intentionally not used here: a Protocol with non-method
    # members (name/model are data attributes, not methods) doesn't support it.
    assert Runner not in FakeRunner.__bases__
    assert isinstance(FakeRunner(), Runner)
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_runners_base.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'rosetta_bench.runners'`

- [x] **Step 3: Write minimal implementation**

```python
# src/rosetta_bench/runners/__init__.py
```

```python
# src/rosetta_bench/runners/base.py
from typing import Protocol, runtime_checkable

from rosetta_bench.models import RunResult, Task


@runtime_checkable
class Runner(Protocol):
    name: str
    model: str

    def run(self, prompt_text: str, task: Task | None) -> RunResult:
        ...
```

- [x] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_runners_base.py -v`
Expected: 2 passed

- [x] **Step 5: Commit**

```bash
git add src/rosetta_bench/runners/__init__.py src/rosetta_bench/runners/base.py tests/test_runners_base.py
git commit -m "Add Runner protocol"
```

---

### Task 7: Claude runner

**Suggested tool:** Claude Code subagent (this tool benchmarks Claude itself — get the seam right).

**Files:**
- Create: `src/rosetta_bench/runners/claude_runner.py`
- Test: `tests/test_claude_runner.py`

**Interfaces:**
- Consumes: `RunResult`, `Task` (Task 2).
- Produces: `AnthropicClientProtocol` (a `typing.Protocol` with `create_message(self, model: str, prompt: str) -> tuple[str, int, int]`, returning `(response_text, input_tokens, output_tokens)`), `ClaudeRunner(model: str, client: AnthropicClientProtocol)` implementing the `Runner` protocol from Task 6. Used by `harness.py` (Task 12). A real `AnthropicSDKClient` adapter wrapping the `anthropic` package is included but is explicitly excluded from the automated test suite (documented in a module docstring) since it requires a live `ANTHROPIC_API_KEY` and makes a real network call — this satisfies the Global Constraint that no test makes a real network call.

- [x] **Step 1: Write the failing test**

```python
# tests/test_claude_runner.py
from rosetta_bench.models import Task
from rosetta_bench.runners.claude_runner import ClaudeRunner


class FakeAnthropicClient:
    def __init__(self, response_text: str, input_tokens: int, output_tokens: int):
        self.response_text = response_text
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.calls: list[tuple[str, str]] = []

    def create_message(self, model: str, prompt: str) -> tuple[str, int, int]:
        self.calls.append((model, prompt))
        return self.response_text, self.input_tokens, self.output_tokens


def test_run_without_task_sends_prompt_text_verbatim():
    client = FakeAnthropicClient("the answer", 50, 10)
    runner = ClaudeRunner(model="claude-sonnet-5", client=client)

    result = runner.run("What is TASK?", None)

    assert result.raw_output == "the answer"
    assert result.tokens_in == 50
    assert result.tokens_out == 10
    assert result.latency_ms >= 0
    assert client.calls == [("claude-sonnet-5", "What is TASK?")]


def test_run_with_task_appends_instructions_to_prompt():
    client = FakeAnthropicClient("done", 20, 5)
    runner = ClaudeRunner(model="claude-sonnet-5", client=client)
    task = Task(name="validate", instructions="write a validator function")

    runner.run("SCHEMA_VER=1.0\nTASK=X", task)

    sent_prompt = client.calls[0][1]
    assert "SCHEMA_VER=1.0" in sent_prompt
    assert "write a validator function" in sent_prompt


def test_runner_exposes_name_and_model():
    runner = ClaudeRunner(model="claude-sonnet-5", client=FakeAnthropicClient("x", 1, 1))
    assert runner.name == "CLAUDE"
    assert runner.model == "claude-sonnet-5"
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_claude_runner.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'rosetta_bench.runners.claude_runner'`

- [x] **Step 3: Write minimal implementation**

```python
# src/rosetta_bench/runners/claude_runner.py
"""Claude runner. `AnthropicSDKClient` wraps the real `anthropic` package and makes
a live network call -- it is intentionally NOT covered by the automated test suite
(requires ANTHROPIC_API_KEY). `ClaudeRunner` itself is fully tested via a fake
client implementing `AnthropicClientProtocol`.
"""
import time
from typing import Protocol

from rosetta_bench.models import RunResult, Task


class AnthropicClientProtocol(Protocol):
    def create_message(self, model: str, prompt: str) -> tuple[str, int, int]:
        """Returns (response_text, input_tokens, output_tokens)."""
        ...


class ClaudeRunner:
    name = "CLAUDE"

    def __init__(self, model: str, client: AnthropicClientProtocol):
        self.model = model
        self.client = client

    def run(self, prompt_text: str, task: Task | None) -> RunResult:
        full_prompt = prompt_text if task is None else f"{prompt_text}\n\nTask: {task.instructions}"
        start = time.perf_counter()
        response_text, tokens_in, tokens_out = self.client.create_message(self.model, full_prompt)
        latency_ms = (time.perf_counter() - start) * 1000
        return RunResult(
            raw_output=response_text,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            turns=1,
        )


class AnthropicSDKClient:
    """Live adapter around the `anthropic` package. Not covered by automated tests."""

    def __init__(self, api_key: str):
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)

    def create_message(self, model: str, prompt: str) -> tuple[str, int, int]:
        response = self._client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in response.content if hasattr(block, "text"))
        return text, response.usage.input_tokens, response.usage.output_tokens
```

- [x] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_claude_runner.py -v`
Expected: 3 passed

- [x] **Step 5: Commit**

```bash
git add src/rosetta_bench/runners/claude_runner.py tests/test_claude_runner.py
git commit -m "Add Claude runner"
```

---

### Task 8: Azure OpenAI runner

**Suggested tool:** Cline (structurally similar to Task 7's already-established pattern).

**Files:**
- Create: `src/rosetta_bench/runners/azure_openai_runner.py`
- Test: `tests/test_azure_openai_runner.py`

**Interfaces:**
- Consumes: `RunResult`, `Task` (Task 2).
- Produces: `AzureOpenAIClientProtocol` (`create_completion(self, deployment: str, prompt: str) -> tuple[str, int, int]`), `AzureOpenAIRunner(deployment: str, client: AzureOpenAIClientProtocol)` implementing `Runner`. A live `AzureOpenAISDKClient` adapter is included, excluded from the test suite (needs `AZURE_OPENAI_API_KEY`/`AZURE_OPENAI_ENDPOINT`).

- [x] **Step 1: Write the failing test**

```python
# tests/test_azure_openai_runner.py
from rosetta_bench.models import Task
from rosetta_bench.runners.azure_openai_runner import AzureOpenAIRunner


class FakeAzureOpenAIClient:
    def __init__(self, response_text: str, input_tokens: int, output_tokens: int):
        self.response_text = response_text
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.calls: list[tuple[str, str]] = []

    def create_completion(self, deployment: str, prompt: str) -> tuple[str, int, int]:
        self.calls.append((deployment, prompt))
        return self.response_text, self.input_tokens, self.output_tokens


def test_run_without_task_sends_prompt_text_verbatim():
    client = FakeAzureOpenAIClient("the answer", 50, 10)
    runner = AzureOpenAIRunner(deployment="gpt-4o", client=client)

    result = runner.run("What is TASK?", None)

    assert result.raw_output == "the answer"
    assert result.tokens_in == 50
    assert result.tokens_out == 10
    assert client.calls == [("gpt-4o", "What is TASK?")]


def test_run_with_task_appends_instructions_to_prompt():
    client = FakeAzureOpenAIClient("done", 20, 5)
    runner = AzureOpenAIRunner(deployment="gpt-4o", client=client)
    task = Task(name="validate", instructions="write a validator function")

    runner.run("SCHEMA_VER=1.0\nTASK=X", task)

    sent_prompt = client.calls[0][1]
    assert "SCHEMA_VER=1.0" in sent_prompt
    assert "write a validator function" in sent_prompt


def test_runner_exposes_name_and_model():
    runner = AzureOpenAIRunner(deployment="gpt-4o", client=FakeAzureOpenAIClient("x", 1, 1))
    assert runner.name == "AZURE_OPENAI"
    assert runner.model == "gpt-4o"
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_azure_openai_runner.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'rosetta_bench.runners.azure_openai_runner'`

- [x] **Step 3: Write minimal implementation**

```python
# src/rosetta_bench/runners/azure_openai_runner.py
"""Azure OpenAI runner. `AzureOpenAISDKClient` makes a live network call -- not
covered by the automated test suite (requires AZURE_OPENAI_API_KEY/ENDPOINT).
`AzureOpenAIRunner` is fully tested via a fake client.
"""
import time
from typing import Protocol

from rosetta_bench.models import RunResult, Task


class AzureOpenAIClientProtocol(Protocol):
    def create_completion(self, deployment: str, prompt: str) -> tuple[str, int, int]:
        """Returns (response_text, input_tokens, output_tokens)."""
        ...


class AzureOpenAIRunner:
    name = "AZURE_OPENAI"

    def __init__(self, deployment: str, client: AzureOpenAIClientProtocol):
        self.model = deployment
        self.client = client

    def run(self, prompt_text: str, task: Task | None) -> RunResult:
        full_prompt = prompt_text if task is None else f"{prompt_text}\n\nTask: {task.instructions}"
        start = time.perf_counter()
        response_text, tokens_in, tokens_out = self.client.create_completion(self.model, full_prompt)
        latency_ms = (time.perf_counter() - start) * 1000
        return RunResult(
            raw_output=response_text,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            turns=1,
        )


class AzureOpenAISDKClient:
    """Live adapter around the `openai` package configured for Azure. Not covered by tests."""

    def __init__(self, api_key: str, endpoint: str, api_version: str = "2024-06-01"):
        from openai import AzureOpenAI

        self._client = AzureOpenAI(api_key=api_key, azure_endpoint=endpoint, api_version=api_version)

    def create_completion(self, deployment: str, prompt: str) -> tuple[str, int, int]:
        response = self._client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.choices[0].message.content or ""
        return text, response.usage.prompt_tokens, response.usage.completion_tokens
```

- [x] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_azure_openai_runner.py -v`
Expected: 3 passed

- [x] **Step 5: Commit**

```bash
git add src/rosetta_bench/runners/azure_openai_runner.py tests/test_azure_openai_runner.py
git commit -m "Add Azure OpenAI runner"
```

---

### Task 9: Ollama runner

**Suggested tool:** Cline (structurally similar to Tasks 7-8's established pattern).

**Files:**
- Create: `src/rosetta_bench/runners/ollama_runner.py`
- Test: `tests/test_ollama_runner.py`

**Interfaces:**
- Consumes: `RunResult`, `Task` (Task 2).
- Produces: `OllamaClientProtocol` (`generate(self, model: str, prompt: str) -> tuple[str, int, int]`), `OllamaRunner(model: str, client: OllamaClientProtocol)` implementing `Runner`. A live `OllamaHTTPClient` adapter (plain HTTP via stdlib `urllib.request`, no extra dependency, since Ollama's local server has no official Python SDK dependency requirement here) is included, excluded from the test suite (needs a running local Ollama server).

- [x] **Step 1: Write the failing test**

```python
# tests/test_ollama_runner.py
from rosetta_bench.models import Task
from rosetta_bench.runners.ollama_runner import OllamaRunner


class FakeOllamaClient:
    def __init__(self, response_text: str, input_tokens: int, output_tokens: int):
        self.response_text = response_text
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.calls: list[tuple[str, str]] = []

    def generate(self, model: str, prompt: str) -> tuple[str, int, int]:
        self.calls.append((model, prompt))
        return self.response_text, self.input_tokens, self.output_tokens


def test_run_without_task_sends_prompt_text_verbatim():
    client = FakeOllamaClient("the answer", 50, 10)
    runner = OllamaRunner(model="llama3", client=client)

    result = runner.run("What is TASK?", None)

    assert result.raw_output == "the answer"
    assert result.tokens_in == 50
    assert result.tokens_out == 10
    assert client.calls == [("llama3", "What is TASK?")]


def test_run_with_task_appends_instructions_to_prompt():
    client = FakeOllamaClient("done", 20, 5)
    runner = OllamaRunner(model="llama3", client=client)
    task = Task(name="validate", instructions="write a validator function")

    runner.run("SCHEMA_VER=1.0\nTASK=X", task)

    sent_prompt = client.calls[0][1]
    assert "SCHEMA_VER=1.0" in sent_prompt
    assert "write a validator function" in sent_prompt


def test_runner_exposes_name_and_model():
    runner = OllamaRunner(model="llama3", client=FakeOllamaClient("x", 1, 1))
    assert runner.name == "OLLAMA"
    assert runner.model == "llama3"
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ollama_runner.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'rosetta_bench.runners.ollama_runner'`

- [x] **Step 3: Write minimal implementation**

```python
# src/rosetta_bench/runners/ollama_runner.py
"""Ollama runner. `OllamaHTTPClient` makes a live HTTP call to a local Ollama
server -- not covered by the automated test suite (requires a running server).
`OllamaRunner` is fully tested via a fake client.
"""
import json
import time
import urllib.request
from typing import Protocol

from rosetta_bench.models import RunResult, Task


class OllamaClientProtocol(Protocol):
    def generate(self, model: str, prompt: str) -> tuple[str, int, int]:
        """Returns (response_text, input_tokens, output_tokens)."""
        ...


class OllamaRunner:
    name = "OLLAMA"

    def __init__(self, model: str, client: OllamaClientProtocol):
        self.model = model
        self.client = client

    def run(self, prompt_text: str, task: Task | None) -> RunResult:
        full_prompt = prompt_text if task is None else f"{prompt_text}\n\nTask: {task.instructions}"
        start = time.perf_counter()
        response_text, tokens_in, tokens_out = self.client.generate(self.model, full_prompt)
        latency_ms = (time.perf_counter() - start) * 1000
        return RunResult(
            raw_output=response_text,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            turns=1,
        )


class OllamaHTTPClient:
    """Live adapter over Ollama's local HTTP API. Not covered by tests."""

    def __init__(self, host: str):
        self._host = host.rstrip("/")

    def generate(self, model: str, prompt: str) -> tuple[str, int, int]:
        payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
        request = urllib.request.Request(
            f"{self._host}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["response"], data.get("prompt_eval_count", 0), data.get("eval_count", 0)
```

- [x] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ollama_runner.py -v`
Expected: 3 passed

- [x] **Step 5: Commit**

```bash
git add src/rosetta_bench/runners/ollama_runner.py tests/test_ollama_runner.py
git commit -m "Add Ollama runner"
```

---

### Task 10: Azure Translation runner (Suite A only)

**Suggested tool:** Claude Code subagent (this runner has the documented asymmetry — no `task` parameter usage — and needs care to not silently pretend to support Suite B).

**Files:**
- Create: `src/rosetta_bench/runners/azure_translation_runner.py`
- Test: `tests/test_azure_translation_runner.py`

**Interfaces:**
- Consumes: `RunResult`, `Task` (Task 2).
- Produces: `AzureTranslationClientProtocol` (`translate(self, text: str, to_language: str) -> str`), `AzureTranslationRunner(client: AzureTranslationClientProtocol, round_trip_language: str = "fr")` implementing `Runner`. Unlike the other three runners, `run()` ignores `task` entirely (raises `ValueError` if a `Task` is passed, since this runner is Suite-A-only per the spec) and instead performs a round-trip translation (`prompt_text` -> `round_trip_language` -> back to English) as the "output" to be scored for comprehension. A live `AzureTranslatorSDKClient` adapter is included, excluded from the test suite (needs `AZURE_TRANSLATOR_API_KEY`).

- [x] **Step 1: Write the failing test**

```python
# tests/test_azure_translation_runner.py
import pytest
from rosetta_bench.models import Task
from rosetta_bench.runners.azure_translation_runner import AzureTranslationRunner


class FakeTranslationClient:
    def __init__(self, forward_text: str, back_text: str):
        self.forward_text = forward_text
        self.back_text = back_text
        self.calls: list[tuple[str, str]] = []

    def translate(self, text: str, to_language: str) -> str:
        self.calls.append((text, to_language))
        return self.back_text if to_language == "en" else self.forward_text


def test_run_performs_round_trip_translation():
    client = FakeTranslationClient(forward_text="texte franc", back_text="round tripped text")
    runner = AzureTranslationRunner(client=client, round_trip_language="fr")

    result = runner.run("SCHEMA_VER=1.0\nTASK=X", None)

    assert result.raw_output == "round tripped text"
    assert client.calls == [("SCHEMA_VER=1.0\nTASK=X", "fr"), ("texte franc", "en")]


def test_run_rejects_a_task_since_this_runner_is_suite_a_only():
    client = FakeTranslationClient(forward_text="x", back_text="y")
    runner = AzureTranslationRunner(client=client)
    task = Task(name="validate", instructions="write a validator function")

    with pytest.raises(ValueError, match="Suite A"):
        runner.run("some prompt", task)


def test_runner_exposes_name_and_model():
    runner = AzureTranslationRunner(client=FakeTranslationClient("x", "y"), round_trip_language="de")
    assert runner.name == "AZURE_TRANSLATION"
    assert runner.model == "de"
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_azure_translation_runner.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'rosetta_bench.runners.azure_translation_runner'`

- [x] **Step 3: Write minimal implementation**

```python
# src/rosetta_bench/runners/azure_translation_runner.py
"""Azure Translation runner. Suite A (comprehension) only -- Azure Translation
doesn't accept arbitrary task instructions, so `run()` raises if given a Task,
per the spec's documented asymmetry. `AzureTranslatorSDKClient` makes a live
network call -- not covered by the automated test suite (requires
AZURE_TRANSLATOR_API_KEY). `AzureTranslationRunner` is fully tested via a fake
client.
"""
import time
from typing import Protocol

from rosetta_bench.models import RunResult, Task


class AzureTranslationClientProtocol(Protocol):
    def translate(self, text: str, to_language: str) -> str:
        ...


class AzureTranslationRunner:
    name = "AZURE_TRANSLATION"

    def __init__(self, client: AzureTranslationClientProtocol, round_trip_language: str = "fr"):
        self.client = client
        self.model = round_trip_language

    def run(self, prompt_text: str, task: Task | None) -> RunResult:
        if task is not None:
            raise ValueError("AzureTranslationRunner is Suite A only and does not accept a Task")
        start = time.perf_counter()
        forward_text = self.client.translate(prompt_text, self.model)
        back_text = self.client.translate(forward_text, "en")
        latency_ms = (time.perf_counter() - start) * 1000
        return RunResult(
            raw_output=back_text,
            tokens_in=len(prompt_text.split()),
            tokens_out=len(back_text.split()),
            latency_ms=latency_ms,
            turns=2,
        )


class AzureTranslatorSDKClient:
    """Live adapter around the Azure Translator REST API. Not covered by tests."""

    def __init__(self, api_key: str, endpoint: str, region: str):
        self._api_key = api_key
        self._endpoint = endpoint.rstrip("/")
        self._region = region

    def translate(self, text: str, to_language: str) -> str:
        import json
        import urllib.request

        url = f"{self._endpoint}/translate?api-version=3.0&to={to_language}"
        payload = json.dumps([{"text": text}]).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Ocp-Apim-Subscription-Key": self._api_key,
                "Ocp-Apim-Subscription-Region": self._region,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data[0]["translations"][0]["text"]
```

- [x] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_azure_translation_runner.py -v`
Expected: 3 passed

- [x] **Step 5: Commit**

```bash
git add src/rosetta_bench/runners/azure_translation_runner.py tests/test_azure_translation_runner.py
git commit -m "Add Azure Translation runner (Suite A only)"
```

---

### Task 11: Trial storage

**Suggested tool:** Codex (straightforward CSV read/append logic).

**Files:**
- Create: `src/rosetta_bench/storage.py`
- Test: `tests/test_storage.py`

**Interfaces:**
- Consumes: `Trial` (Task 2, `.to_row()`).
- Produces: `append_trial(trial: Trial, path: Path) -> None` (creates the file with a header row if it doesn't exist, appends otherwise) and `load_trials(path: Path) -> list[dict]`. Used by `harness.py` (Task 12) and both exporters (Tasks 13-14).

- [x] **Step 1: Write the failing test**

```python
# tests/test_storage.py
from pathlib import Path
from rosetta_bench.models import Trial
from rosetta_bench.storage import append_trial, load_trials


def _make_trial(trial_id: str) -> Trial:
    return Trial(
        trial_id=trial_id, timestamp="2026-07-13T00:00:00Z", tool="CLAUDE", model="claude-sonnet-5",
        prompt_id="rosetta_build", prompt_format="MACHINE", suite="COMPREHENSION",
        tokens_in=100, tokens_out=20, latency_ms=456.0, turns=1, task_success=None,
        comprehension_accuracy=0.9, quality_score=None, judge_justification="",
        cost_usd=0.001, raw_output="the answer",
    )


def test_append_trial_creates_file_with_header(tmp_path: Path):
    path = tmp_path / "trials.csv"
    append_trial(_make_trial("t1"), path)

    rows = load_trials(path)
    assert len(rows) == 1
    assert rows[0]["trial_id"] == "t1"
    assert rows[0]["tool"] == "CLAUDE"


def test_append_trial_appends_without_duplicating_header(tmp_path: Path):
    path = tmp_path / "trials.csv"
    append_trial(_make_trial("t1"), path)
    append_trial(_make_trial("t2"), path)

    rows = load_trials(path)
    assert len(rows) == 2
    assert [r["trial_id"] for r in rows] == ["t1", "t2"]
    header_line = path.read_text(encoding="utf-8").splitlines()[0]
    assert header_line.count("trial_id") == 1
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_storage.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'rosetta_bench.storage'`

- [x] **Step 3: Write minimal implementation**

```python
# src/rosetta_bench/storage.py
import csv
from pathlib import Path

from rosetta_bench.models import Trial

_COLUMNS = [
    "trial_id", "timestamp", "tool", "model", "prompt_id", "prompt_format",
    "suite", "tokens_in", "tokens_out", "latency_ms", "turns", "task_success",
    "comprehension_accuracy", "quality_score", "judge_justification",
    "cost_usd", "raw_output",
]


def append_trial(trial: Trial, path: Path) -> None:
    file_exists = path.exists()
    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_COLUMNS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(trial.to_row())


def load_trials(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))
```

- [x] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_storage.py -v`
Expected: 2 passed

- [x] **Step 5: Commit**

```bash
git add src/rosetta_bench/storage.py tests/test_storage.py
git commit -m "Add trial CSV storage (append + load)"
```

---

### Task 12: Harness orchestration

**Suggested tool:** Claude Code subagent (ties every earlier task together — highest integration risk in the plan).

**Files:**
- Create: `src/rosetta_bench/harness.py`
- Test: `tests/test_harness.py`

**Interfaces:**
- Consumes: `Case` (Task 4), `Runner`/`RunResult`/`Task` (Tasks 2, 6), `score_trial`/`JudgeCallFn` (Task 5), `estimate_cost` (Task 3), `append_trial` (Task 11).
- Produces: `run_trial(runner: Runner, case: Case, prompt_format: str, suite: str, judge_call_fn: JudgeCallFn | None, trial_id: str, timestamp: str) -> Trial`. `prompt_format` is `"HUMAN"` or `"MACHINE"` (selects `case.human_text`/`case.machine_text`); `suite` is `"COMPREHENSION"` or `"TASK_COMPLETION"`. For `COMPREHENSION`, no `Task` is passed to the runner and `comprehension_accuracy` is left `None` in this task (scoring the answer against `answer_key` is a separate concern noted as an open item, not built here — see Task 12's Step 3 comment). For `TASK_COMPLETION`, a `Task` built from `case.task_spec` is passed to the runner, and if `judge_call_fn` is provided, `score_trial` is called and `quality_score`/`judge_justification` are populated.

- [x] **Step 1: Write the failing test**

```python
# tests/test_harness.py
from rosetta_bench.corpus import Case
from rosetta_bench.harness import run_trial
from rosetta_bench.models import RunResult, Task


class FakeRunner:
    name = "FAKE"
    model = "fake-model-v1"

    def __init__(self, response_text: str = "fake output"):
        self.response_text = response_text
        self.received_tasks: list[Task | None] = []

    def run(self, prompt_text: str, task) -> RunResult:
        self.received_tasks.append(task)
        return RunResult(raw_output=self.response_text, tokens_in=10, tokens_out=5, latency_ms=42.0)


def _make_case() -> Case:
    return Case(
        case_id="rosetta_build",
        human_text="# Human doc",
        machine_text="SCHEMA_VER=1.0\nTASK=X",
        answer_key=[{"question": "What is TASK?", "answer": "X"}],
        task_spec={"name": "validate", "instructions": "write a validator", "reference_output": None},
    )


def test_comprehension_trial_sends_no_task_and_selects_machine_text():
    runner = FakeRunner()
    case = _make_case()

    trial = run_trial(runner, case, "MACHINE", "COMPREHENSION", judge_call_fn=None, trial_id="t1", timestamp="2026-07-13T00:00:00Z")

    assert runner.received_tasks == [None]
    assert trial.prompt_format == "MACHINE"
    assert trial.suite == "COMPREHENSION"
    assert trial.comprehension_accuracy is None
    assert trial.quality_score is None
    assert trial.tool == "FAKE"
    assert trial.cost_usd == 0.0  # unknown (tool, model) pair per pricing.py


def test_task_completion_trial_sends_task_built_from_case_spec():
    runner = FakeRunner()
    case = _make_case()

    trial = run_trial(runner, case, "HUMAN", "TASK_COMPLETION", judge_call_fn=None, trial_id="t2", timestamp="2026-07-13T00:00:00Z")

    assert runner.received_tasks[0].instructions == "write a validator"
    assert trial.prompt_format == "HUMAN"
    assert trial.suite == "TASK_COMPLETION"


def test_task_completion_trial_invokes_judge_when_provided():
    runner = FakeRunner(response_text="my validator implementation")

    def fake_judge_call_fn(prompt: str) -> str:
        assert "my validator implementation" in prompt
        return "CORRECTNESS: 5\nCOMPLETENESS: 4\nFAITHFULNESS: 5\nCLARITY: 4\nJUSTIFICATION: Solid.\n"

    case = _make_case()
    trial = run_trial(runner, case, "HUMAN", "TASK_COMPLETION", judge_call_fn=fake_judge_call_fn, trial_id="t3", timestamp="2026-07-13T00:00:00Z")

    assert trial.quality_score == 4.5
    assert "Solid" in trial.judge_justification
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_harness.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'rosetta_bench.harness'`

- [x] **Step 3: Write minimal implementation**

```python
# src/rosetta_bench/harness.py
from rosetta_bench.corpus import Case
from rosetta_bench.judge import JudgeCallFn, score_trial
from rosetta_bench.models import Task, Trial
from rosetta_bench.pricing import estimate_cost
from rosetta_bench.runners.base import Runner


def run_trial(
    runner: Runner,
    case: Case,
    prompt_format: str,
    suite: str,
    judge_call_fn: JudgeCallFn | None,
    trial_id: str,
    timestamp: str,
) -> Trial:
    prompt_text = case.human_text if prompt_format == "HUMAN" else case.machine_text

    task: Task | None = None
    if suite == "TASK_COMPLETION":
        task = Task(
            name=case.task_spec["name"],
            instructions=case.task_spec["instructions"],
            reference_output=case.task_spec.get("reference_output"),
        )

    result = runner.run(prompt_text, task)

    quality_score = None
    judge_justification = ""
    if suite == "TASK_COMPLETION" and judge_call_fn is not None:
        judge_result = score_trial(
            task.instructions, result.raw_output, task.reference_output, judge_call_fn
        )
        quality_score = judge_result.mean_score
        judge_justification = judge_result.justification

    cost_usd = estimate_cost(runner.name, runner.model, result.tokens_in, result.tokens_out)

    return Trial(
        trial_id=trial_id,
        timestamp=timestamp,
        tool=runner.name,
        model=runner.model,
        prompt_id=case.case_id,
        prompt_format=prompt_format,
        suite=suite,
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
        latency_ms=result.latency_ms,
        turns=result.turns,
        task_success=None,
        comprehension_accuracy=None,  # answer-key scoring is a documented follow-up, not built here
        quality_score=quality_score,
        judge_justification=judge_justification,
        cost_usd=cost_usd,
        raw_output=result.raw_output,
    )
```

- [x] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_harness.py -v`
Expected: 3 passed

- [x] **Step 5: Commit**

```bash
git add src/rosetta_bench/harness.py tests/test_harness.py
git commit -m "Add harness trial orchestration"
```

---

### Task 13: xlsx export

**Suggested tool:** Cline (benefits from interactively opening the generated file to check formatting).

**Files:**
- Create: `src/rosetta_bench/export_xlsx.py`
- Test: `tests/test_export_xlsx.py`

**Interfaces:**
- Consumes: `load_trials` (Task 11).
- Produces: `export_to_xlsx(csv_path: Path, xlsx_path: Path) -> None`. Writes a workbook with two sheets: `raw_data` (every row/column from the CSV, header included) and `summary` (mean `latency_ms`, mean `tokens_in`, mean `tokens_out`, mean `quality_score`, mean `cost_usd`, grouped by `(tool, prompt_format)`).

- [x] **Step 1: Write the failing test**

```python
# tests/test_export_xlsx.py
from pathlib import Path
import openpyxl
from rosetta_bench.export_xlsx import export_to_xlsx
from rosetta_bench.models import Trial
from rosetta_bench.storage import append_trial


def _make_trial(trial_id: str, tool: str, prompt_format: str, latency_ms: float) -> Trial:
    return Trial(
        trial_id=trial_id, timestamp="2026-07-13T00:00:00Z", tool=tool, model="m1",
        prompt_id="rosetta_build", prompt_format=prompt_format, suite="TASK_COMPLETION",
        tokens_in=100, tokens_out=20, latency_ms=latency_ms, turns=1, task_success=None,
        comprehension_accuracy=None, quality_score=4.0, judge_justification="ok",
        cost_usd=0.01, raw_output="output",
    )


def test_export_creates_raw_data_and_summary_sheets(tmp_path: Path):
    csv_path = tmp_path / "trials.csv"
    append_trial(_make_trial("t1", "CLAUDE", "MACHINE", 100.0), csv_path)
    append_trial(_make_trial("t2", "CLAUDE", "MACHINE", 200.0), csv_path)
    append_trial(_make_trial("t3", "CLAUDE", "HUMAN", 500.0), csv_path)
    xlsx_path = tmp_path / "trials.xlsx"

    export_to_xlsx(csv_path, xlsx_path)

    workbook = openpyxl.load_workbook(xlsx_path)
    assert set(workbook.sheetnames) == {"raw_data", "summary"}

    raw_sheet = workbook["raw_data"]
    assert raw_sheet["A1"].value == "trial_id"
    assert raw_sheet.max_row == 4  # header + 3 rows

    summary_sheet = workbook["summary"]
    summary_rows = list(summary_sheet.iter_rows(values_only=True))
    assert summary_rows[0] == ("tool", "prompt_format", "mean_latency_ms", "mean_tokens_in", "mean_tokens_out", "mean_quality_score", "mean_cost_usd", "n")
    machine_row = next(r for r in summary_rows[1:] if r[0] == "CLAUDE" and r[1] == "MACHINE")
    assert machine_row[2] == 150.0  # mean of 100.0 and 200.0
    assert machine_row[7] == 2  # n
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_export_xlsx.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'rosetta_bench.export_xlsx'`

- [x] **Step 3: Write minimal implementation**

```python
# src/rosetta_bench/export_xlsx.py
from collections import defaultdict
from pathlib import Path

import openpyxl

from rosetta_bench.storage import load_trials

_SUMMARY_HEADER = (
    "tool", "prompt_format", "mean_latency_ms", "mean_tokens_in",
    "mean_tokens_out", "mean_quality_score", "mean_cost_usd", "n",
)


def export_to_xlsx(csv_path: Path, xlsx_path: Path) -> None:
    rows = load_trials(csv_path)

    workbook = openpyxl.Workbook()
    raw_sheet = workbook.active
    raw_sheet.title = "raw_data"
    if rows:
        raw_sheet.append(list(rows[0].keys()))
        for row in rows:
            raw_sheet.append(list(row.values()))

    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        groups[(row["tool"], row["prompt_format"])].append(row)

    summary_sheet = workbook.create_sheet("summary")
    summary_sheet.append(list(_SUMMARY_HEADER))
    for (tool, prompt_format), group_rows in sorted(groups.items()):
        n = len(group_rows)
        latencies = [float(r["latency_ms"]) for r in group_rows]
        tokens_in = [float(r["tokens_in"]) for r in group_rows]
        tokens_out = [float(r["tokens_out"]) for r in group_rows]
        quality_scores = [float(r["quality_score"]) for r in group_rows if r["quality_score"]]
        costs = [float(r["cost_usd"]) for r in group_rows]
        summary_sheet.append([
            tool,
            prompt_format,
            sum(latencies) / n,
            sum(tokens_in) / n,
            sum(tokens_out) / n,
            (sum(quality_scores) / len(quality_scores)) if quality_scores else None,
            sum(costs) / n,
            n,
        ])

    workbook.save(xlsx_path)
```

- [x] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_export_xlsx.py -v`
Expected: 1 passed

- [x] **Step 5: Commit**

```bash
git add src/rosetta_bench/export_xlsx.py tests/test_export_xlsx.py
git commit -m "Add xlsx export with raw-data and summary sheets"
```

---

### Task 14: Google Sheets export

**Suggested tool:** Cline (needs interactive credential setup/testing).

**Files:**
- Create: `src/rosetta_bench/export_sheets.py`
- Test: `tests/test_export_sheets.py`

**Interfaces:**
- Consumes: `load_trials` (Task 11).
- Produces: `GSpreadClientProtocol` (`open_or_create(self, sheet_name: str) -> "SpreadsheetProtocol"`, where `SpreadsheetProtocol` has `update_sheet(self, worksheet_name: str, rows: list[list])`), `export_to_sheets(csv_path: Path, sheet_name: str, client: GSpreadClientProtocol) -> None`, mirroring `export_to_xlsx`'s two-sheet structure (`raw_data`, `summary`) but writing via the injected client instead of a file. A live `GSpreadClient` adapter wrapping the real `gspread` package (using `GOOGLE_SERVICE_ACCOUNT_JSON`) is included, excluded from the test suite (needs live Google credentials).

- [x] **Step 1: Write the failing test**

```python
# tests/test_export_sheets.py
from pathlib import Path
from rosetta_bench.export_sheets import export_to_sheets
from rosetta_bench.models import Trial
from rosetta_bench.storage import append_trial


class FakeSpreadsheet:
    def __init__(self):
        self.worksheets: dict[str, list[list]] = {}

    def update_sheet(self, worksheet_name: str, rows: list[list]) -> None:
        self.worksheets[worksheet_name] = rows


class FakeGSpreadClient:
    def __init__(self):
        self.spreadsheet = FakeSpreadsheet()
        self.opened_names: list[str] = []

    def open_or_create(self, sheet_name: str):
        self.opened_names.append(sheet_name)
        return self.spreadsheet


def _make_trial(trial_id: str, tool: str, prompt_format: str) -> Trial:
    return Trial(
        trial_id=trial_id, timestamp="2026-07-13T00:00:00Z", tool=tool, model="m1",
        prompt_id="rosetta_build", prompt_format=prompt_format, suite="TASK_COMPLETION",
        tokens_in=100, tokens_out=20, latency_ms=150.0, turns=1, task_success=None,
        comprehension_accuracy=None, quality_score=4.0, judge_justification="ok",
        cost_usd=0.01, raw_output="output",
    )


def test_export_opens_named_sheet_and_writes_both_worksheets(tmp_path: Path):
    csv_path = tmp_path / "trials.csv"
    append_trial(_make_trial("t1", "CLAUDE", "MACHINE"), csv_path)
    client = FakeGSpreadClient()

    export_to_sheets(csv_path, "rosetta-bench results", client)

    assert client.opened_names == ["rosetta-bench results"]
    assert "raw_data" in client.spreadsheet.worksheets
    assert "summary" in client.spreadsheet.worksheets
    raw_rows = client.spreadsheet.worksheets["raw_data"]
    assert raw_rows[0][0] == "trial_id"
    assert raw_rows[1][0] == "t1"
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_export_sheets.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'rosetta_bench.export_sheets'`

- [x] **Step 3: Write minimal implementation**

```python
# src/rosetta_bench/export_sheets.py
"""Google Sheets export. `GSpreadClient` makes live Google API calls -- not
covered by the automated test suite (requires GOOGLE_SERVICE_ACCOUNT_JSON).
`export_to_sheets` itself is fully tested via a fake client.
"""
from collections import defaultdict
from pathlib import Path
from typing import Protocol

from rosetta_bench.storage import load_trials

_SUMMARY_HEADER = [
    "tool", "prompt_format", "mean_latency_ms", "mean_tokens_in",
    "mean_tokens_out", "mean_quality_score", "mean_cost_usd", "n",
]


class SpreadsheetProtocol(Protocol):
    def update_sheet(self, worksheet_name: str, rows: list[list]) -> None:
        ...


class GSpreadClientProtocol(Protocol):
    def open_or_create(self, sheet_name: str) -> SpreadsheetProtocol:
        ...


def export_to_sheets(csv_path: Path, sheet_name: str, client: GSpreadClientProtocol) -> None:
    rows = load_trials(csv_path)
    spreadsheet = client.open_or_create(sheet_name)

    raw_rows: list[list] = []
    if rows:
        raw_rows.append(list(rows[0].keys()))
        for row in rows:
            raw_rows.append(list(row.values()))
    spreadsheet.update_sheet("raw_data", raw_rows)

    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        groups[(row["tool"], row["prompt_format"])].append(row)

    summary_rows: list[list] = [list(_SUMMARY_HEADER)]
    for (tool, prompt_format), group_rows in sorted(groups.items()):
        n = len(group_rows)
        latencies = [float(r["latency_ms"]) for r in group_rows]
        tokens_in = [float(r["tokens_in"]) for r in group_rows]
        tokens_out = [float(r["tokens_out"]) for r in group_rows]
        quality_scores = [float(r["quality_score"]) for r in group_rows if r["quality_score"]]
        costs = [float(r["cost_usd"]) for r in group_rows]
        summary_rows.append([
            tool,
            prompt_format,
            sum(latencies) / n,
            sum(tokens_in) / n,
            sum(tokens_out) / n,
            (sum(quality_scores) / len(quality_scores)) if quality_scores else None,
            sum(costs) / n,
            n,
        ])
    spreadsheet.update_sheet("summary", summary_rows)


class GSpreadClient:
    """Live adapter around the `gspread` package. Not covered by tests."""

    def __init__(self, service_account_json_path: str):
        import gspread

        self._client = gspread.service_account(filename=service_account_json_path)

    def open_or_create(self, sheet_name: str):
        try:
            spreadsheet = self._client.open(sheet_name)
        except Exception:
            spreadsheet = self._client.create(sheet_name)
        return _GSpreadSpreadsheetAdapter(spreadsheet)


class _GSpreadSpreadsheetAdapter:
    def __init__(self, spreadsheet):
        self._spreadsheet = spreadsheet

    def update_sheet(self, worksheet_name: str, rows: list[list]) -> None:
        try:
            worksheet = self._spreadsheet.worksheet(worksheet_name)
        except Exception:
            worksheet = self._spreadsheet.add_worksheet(title=worksheet_name, rows=1, cols=1)
        worksheet.clear()
        if rows:
            worksheet.update(rows)
```

- [x] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_export_sheets.py -v`
Expected: 1 passed

- [x] **Step 5: Commit**

```bash
git add src/rosetta_bench/export_sheets.py tests/test_export_sheets.py
git commit -m "Add Google Sheets export"
```

---

### Task 15: CLI

**Suggested tool:** Cline (CLI UX benefits from interactively running commands).

**Files:**
- Create: `src/rosetta_bench/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `export_to_xlsx` (Task 13), `export_to_sheets`/`GSpreadClient` (Task 14). `run` subcommand wiring to the harness/runners is deliberately deferred (see Step 3's comment) since it requires live credentials to be meaningful and is exercised manually, not by this task's tests — this task covers the `export` subcommands fully, and stubs `run` with a clear NotImplementedError message rather than pretending to wire up untestable live-API orchestration.
- Produces: `main(argv: list[str] | None = None) -> int`, wired as the `bench` console script via `pyproject.toml` (Task 1). Subcommands: `export xlsx --csv PATH --out PATH`, `export sheets --csv PATH --sheet-name NAME` (requires `GOOGLE_SERVICE_ACCOUNT_JSON` env var), `run` (prints a message directing the user to invoke the harness directly with real credentials; not part of this task's automated scope).

- [x] **Step 1: Write the failing test**

```python
# tests/test_cli.py
from pathlib import Path
from rosetta_bench.cli import main
from rosetta_bench.models import Trial
from rosetta_bench.storage import append_trial


def _make_trial(trial_id: str) -> Trial:
    return Trial(
        trial_id=trial_id, timestamp="2026-07-13T00:00:00Z", tool="CLAUDE", model="m1",
        prompt_id="rosetta_build", prompt_format="MACHINE", suite="TASK_COMPLETION",
        tokens_in=10, tokens_out=5, latency_ms=100.0, turns=1, task_success=None,
        comprehension_accuracy=None, quality_score=4.0, judge_justification="ok",
        cost_usd=0.01, raw_output="output",
    )


def test_export_xlsx_command_writes_file(tmp_path: Path):
    csv_path = tmp_path / "trials.csv"
    append_trial(_make_trial("t1"), csv_path)
    xlsx_path = tmp_path / "out.xlsx"

    code = main(["export", "xlsx", "--csv", str(csv_path), "--out", str(xlsx_path)])

    assert code == 0
    assert xlsx_path.exists()


def test_run_command_returns_nonzero_and_explains_manual_invocation(capsys):
    code = main(["run"])

    assert code == 1
    captured = capsys.readouterr()
    assert "not automated" in captured.err.lower() or "credentials" in captured.err.lower()
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'rosetta_bench.cli'`

- [x] **Step 3: Write minimal implementation**

```python
# src/rosetta_bench/cli.py
import argparse
import sys
from pathlib import Path

from rosetta_bench.export_xlsx import export_to_xlsx


def _run_export_xlsx(csv_path: Path, out_path: Path) -> int:
    export_to_xlsx(csv_path, out_path)
    print(f"wrote {out_path}")
    return 0


def _run_export_sheets(csv_path: Path, sheet_name: str) -> int:
    import os

    from rosetta_bench.export_sheets import GSpreadClient, export_to_sheets

    service_account_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not service_account_path:
        print("GOOGLE_SERVICE_ACCOUNT_JSON is not set", file=sys.stderr)
        return 1
    client = GSpreadClient(service_account_path)
    export_to_sheets(csv_path, sheet_name, client)
    print(f"wrote to Google Sheet '{sheet_name}'")
    return 0


def _run_bench(args: argparse.Namespace) -> int:
    # Wiring live runners (Claude/Azure OpenAI/Azure Translation/Ollama) requires
    # real credentials and is exercised manually per-tool, not by this CLI's
    # automated test suite. Construct the harness call yourself using
    # rosetta_bench.harness.run_trial with the concrete SDK/HTTP client adapters
    # from each runner module.
    print(
        "`bench run` is not automated in v1 -- requires live credentials for "
        "each tool. Use rosetta_bench.harness.run_trial directly with the "
        "concrete client adapters (ClaudeRunner + AnthropicSDKClient, etc.).",
        file=sys.stderr,
    )
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bench")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run")

    export_parser = subparsers.add_parser("export")
    export_subparsers = export_parser.add_subparsers(dest="export_format", required=True)

    xlsx_parser = export_subparsers.add_parser("xlsx")
    xlsx_parser.add_argument("--csv", required=True)
    xlsx_parser.add_argument("--out", required=True)

    sheets_parser = export_subparsers.add_parser("sheets")
    sheets_parser.add_argument("--csv", required=True)
    sheets_parser.add_argument("--sheet-name", required=True)

    args = parser.parse_args(argv)

    if args.command == "run":
        return _run_bench(args)
    if args.command == "export" and args.export_format == "xlsx":
        return _run_export_xlsx(Path(args.csv), Path(args.out))
    if args.command == "export" and args.export_format == "sheets":
        return _run_export_sheets(Path(args.csv), args.sheet_name)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [x] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py -v`
Expected: 2 passed

- [x] **Step 5: Commit**

```bash
git add src/rosetta_bench/cli.py tests/test_cli.py
git commit -m "Add bench CLI: export xlsx/sheets, run stub"
```

---

### Task 16: Corpus fixture from Rosetta's dogfooded artifact

**Suggested tool:** Claude Code subagent (requires judgment about what to copy and how to derive the answer key/task spec).

**Files:**
- Create: `corpus/rosetta_build/human.md`
- Create: `corpus/rosetta_build/machine.cpn`
- Create: `corpus/rosetta_build/answer_key.yaml`
- Create: `corpus/rosetta_build/task_spec.yaml`

**Interfaces:**
- Produces: the first real corpus case, loadable via `load_case(Path("corpus"), "rosetta_build")` (Task 4).

- [x] **Step 1: Copy Rosetta's dogfooded artifact files**

```bash
cp "../rosetta/docs/decisions/rosetta_build.md" corpus/rosetta_build/human.md
cp "../rosetta/docs/decisions/rosetta_build.cpn" corpus/rosetta_build/machine.cpn
```

(Adjust the relative path if your `rosetta` checkout is elsewhere; the source files are `docs/decisions/rosetta_build.md` and `docs/decisions/rosetta_build.cpn` in the `rosetta` repo's `master` branch, produced by Rosetta's own Task 11.)

- [x] **Step 2: Write `corpus/rosetta_build/answer_key.yaml`**

Base the questions on the actual fields in `docs/decisions/rosetta_build.fields.json` from the `rosetta` repo. Read that file to confirm exact values before writing this, since it's the ground truth the answer key must match -- the fields present as of Rosetta's own Task 11/12 are `CACHE_STABILITY`, `CONFLICT_POLICY`, `FIELD_VALUE_TYPES`, `NORMAL_PROMPT_VIEW`, `RUNTIME_FALLBACK`, and `TASK` (no `DECISION_COUNT` field exists -- an earlier draft of this plan assumed one before the actual file was checked).

```yaml
- question: "What does CONFLICT_POLICY say about how sync conflicts are resolved?"
  answer: "explicit,no-auto-merge"
- question: "What is the value of NORMAL_PROMPT_VIEW?"
  answer: "CPN"
- question: "What is RUNTIME_FALLBACK set to?"
  answer: "human-markdown"
- question: "What does FIELD_VALUE_TYPES list as the allowed field value types?"
  answer: "str,int,float"
- question: "What does CACHE_STABILITY describe?"
  answer: "canonical-key-order,LF,fixed-floats"
```

- [x] **Step 3: Write `corpus/rosetta_build/task_spec.yaml`**

```yaml
name: summarize_for_new_teammate
instructions: >
  Summarize this policy record for a new teammate joining the Rosetta project
  in 3 bullet points. Explicitly call out NORMAL_PROMPT_VIEW, RUNTIME_FALLBACK,
  and CONFLICT_POLICY, and explain in one sentence why numeric packet values
  are recovered via the JSON Schema rather than type-guessed (see the notes
  in the document for the reason).
reference_output: null
```

- [x] **Step 4: Verify the corpus case loads correctly**

```bash
python -c "
from pathlib import Path
from rosetta_bench.corpus import load_case
case = load_case(Path('corpus'), 'rosetta_build')
assert 'CONFLICT_POLICY' in case.machine_text
assert len(case.answer_key) == 5
assert case.task_spec['name'] == 'summarize_for_new_teammate'
print('OK')
"
```

Expected: `OK`

- [x] **Step 5: Commit**

```bash
git add corpus/rosetta_build/
git commit -m "Add rosetta_build corpus case from Rosetta's dogfooded artifact"
```

---

### Task 17: End-to-end harness test with fakes

**Suggested tool:** Claude Code subagent (integration test spanning the whole system).

**Files:**
- Test: `tests/test_end_to_end.py`

**Interfaces:**
- Consumes: `load_case` (Task 4), `run_trial` (Task 12), `append_trial`/`load_trials` (Task 11), `export_to_xlsx` (Task 13).

- [x] **Step 1: Write the failing test**

```python
# tests/test_end_to_end.py
from pathlib import Path
from rosetta_bench.corpus import load_case
from rosetta_bench.export_xlsx import export_to_xlsx
from rosetta_bench.harness import run_trial
from rosetta_bench.models import RunResult, Task
from rosetta_bench.storage import append_trial, load_trials


class FakeRunner:
    def __init__(self, name: str, model: str, response_text: str):
        self.name = name
        self.model = model
        self.response_text = response_text

    def run(self, prompt_text: str, task: Task | None) -> RunResult:
        return RunResult(raw_output=self.response_text, tokens_in=20, tokens_out=10, latency_ms=50.0)


def _fake_judge(prompt: str) -> str:
    return "CORRECTNESS: 5\nCOMPLETENESS: 5\nFAITHFULNESS: 4\nCLARITY: 5\nJUSTIFICATION: Good summary.\n"


def test_full_lifecycle_load_corpus_run_both_formats_export(tmp_path: Path):
    corpus_dir = Path("corpus")
    case = load_case(corpus_dir, "rosetta_build")

    csv_path = tmp_path / "trials.csv"
    runner_human = FakeRunner("CLAUDE", "claude-sonnet-5", "summary using human doc")
    runner_machine = FakeRunner("CLAUDE", "claude-sonnet-5", "summary using machine packet")

    trial_human = run_trial(runner_human, case, "HUMAN", "TASK_COMPLETION", _fake_judge, "t1", "2026-07-13T00:00:00Z")
    trial_machine = run_trial(runner_machine, case, "MACHINE", "TASK_COMPLETION", _fake_judge, "t2", "2026-07-13T00:00:01Z")
    append_trial(trial_human, csv_path)
    append_trial(trial_machine, csv_path)

    rows = load_trials(csv_path)
    assert len(rows) == 2
    assert {r["prompt_format"] for r in rows} == {"HUMAN", "MACHINE"}
    assert all(float(r["quality_score"]) == 4.75 for r in rows)

    xlsx_path = tmp_path / "trials.xlsx"
    export_to_xlsx(csv_path, xlsx_path)
    assert xlsx_path.exists()
```

- [x] **Step 2: Run test to verify it passes immediately**

This task adds no new production code — every function it calls (`load_case`, `run_trial`, `append_trial`, `load_trials`, `export_to_xlsx`) is already implemented and independently tested. This test only verifies they compose correctly end-to-end using the real `corpus/rosetta_build` fixture from Task 16, so it should pass on the first run rather than fail first.

Run: `pytest tests/test_end_to_end.py -v`
Expected: PASS immediately. If it fails, the bug is in an already-committed task's code (or Task 16's fixture files don't match what this test expects), not in this test — stop and fix the earlier task.

- [x] **Step 3: Run the full test suite**

Run: `pytest -v`
Expected: all tests across every task pass.

- [x] **Step 4: Commit**

```bash
git add tests/test_end_to_end.py
git commit -m "Add end-to-end test: load corpus, run both formats, export"
```

---

## Self-Review Notes

- **Spec coverage:** test suites A/B (Task 12's `run_trial` branches on `suite`), schema (Task 2/11), rubric (Task 5), all four runners (Tasks 7-10) with the documented Azure Translation asymmetry (Task 10), CSV-as-source-of-truth (Task 11), xlsx export (Task 13), Google Sheets export (Task 14), corpus from Rosetta's own artifact (Task 16) — all covered.
- **Deliberately deferred, per the spec's own "Open questions":** `comprehension_accuracy` scoring logic (exact-match vs. LLM-judge) is left `None` in `run_trial` (Task 12) rather than guessed at — implementing it requires the exact-match-vs-judge decision the spec explicitly deferred; wiring it in is a fast-follow once that's decided, not a gap in this plan's own scope. `bench run`'s live orchestration (Task 15) is intentionally a stub for the same reason live API calls are excluded from tests: it needs real credentials to be meaningful, and per-tool live runs are better driven directly via `harness.run_trial` with the concrete adapters until there's a reason to script the exact tool/case/suite matrix.
- **Type consistency:** `Runner.run(prompt_text, task) -> RunResult` signature is identical across the protocol (Task 6) and all four concrete runners (Tasks 7-10); `Trial`'s field names/order (Task 2) match `storage._COLUMNS` (Task 11) and both exporters' raw-data sheet exactly.
