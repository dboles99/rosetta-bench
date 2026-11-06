# rosetta-bench

A small Python harness for comparing how language-model tools handle the same prompt written in two forms: a verbose human-readable Markdown document and a compact machine-readable packet.

**简体中文：** rosetta-bench 用同一份提示词的两种写法（详细的 Markdown 文档与紧凑的 `KEY=VALUE` 数据包）去测试不同的大模型工具，记录耗时、词元数、费用和由模型评委给出的质量分，并导出为 CSV 与 Excel。目前它是一个带测试的框架，尚未发布任何真实模型的测试结果。

**繁體中文：** rosetta-bench 以同一份提示詞的兩種寫法（詳細的 Markdown 文件與精簡的 `KEY=VALUE` 資料包）測試不同的大型語言模型工具，記錄耗時、詞元數、費用與模型評審給出的品質分數，並匯出為 CSV 與 Excel。目前它是一個附有測試的框架，尚未發布任何真實模型的測試結果。

## What it does

- Loads a corpus case: `human.md`, `machine.cpn`, an answer key and a task spec (`corpus/<case>/`).
- Runs a case through a *runner* for one tool. Runners exist for Claude (Anthropic API), Azure OpenAI, Azure Translator (round-trip translation, comprehension suite only) and a local Ollama server.
- Optionally scores the output with an LLM judge on four 1-5 dimensions: correctness, completeness, faithfulness to constraints, clarity.
- Appends one row per trial to a CSV (tool, model, prompt format, suite, tokens, latency, cost, quality score, raw output).
- Exports the CSV to `.xlsx` (raw data sheet plus a per-tool, per-format summary sheet) or to a Google Sheet.

Cost comes from a small static price table in `src/rosetta_bench/pricing.py`. It is a placeholder snapshot that I have not checked against current price lists, and unlisted models cost 0.0. Update it before trusting any cost column.

## Quick start

Needs Python 3.11 or later. The tests and the demo need no API key and no network access.

```bash
git clone <this repository>
cd rosetta-bench
python -m venv .venv
.venv/bin/pip install -e ".[dev]"      # Windows: .venv\Scripts\pip install -e ".[dev]"
.venv/bin/python -m pytest -q          # 38 tests
.venv/bin/python examples/offline_demo.py
```

To use the Azure OpenAI adapter, install the extra: `pip install -e ".[azure]"`. Credentials go in a `.env` file or the environment; copy `.env.example` for the variable names. The `.env` file is ignored by git.

## Example

`examples/offline_demo.py` runs the full path (corpus, harness, judge, CSV, xlsx) with a stub in place of a model. The stub reports the prompt length in characters, so the output describes the corpus, not any model:

```
HUMAN    prompt characters: 1226
MACHINE  prompt characters: 212
```

For a real run, swap the stub for a live runner:

```python
from rosetta_bench.runners.claude_runner import ClaudeRunner, AnthropicSDKClient

runner = ClaudeRunner("<model name>", AnthropicSDKClient(api_key))
trial = run_trial(runner, case, "MACHINE", "TASK_COMPLETION", judge_call_fn, "t1", timestamp)
```

## Design notes

- Two suites: comprehension (factual questions about the prompt) and task completion (a concrete task scored by the judge). They are kept apart so that readability and task outcome are not conflated.
- Each tool is one adapter implementing `Runner.run(prompt_text, task) -> RunResult`. The adapters talk to the network through small client protocols, so the runner logic is tested with fakes.
- The CSV is the single source of truth. The xlsx and Google Sheet are generated from it, never the reverse.
- Design notes from the first version are in [docs/design.md](docs/design.md).

## Limits

- **No published results.** The only corpus case is one tiny example (1,251 bytes human, 219 bytes machine). That is far too small to support any claim about which format is better.
- **`bench run` is a stub.** It prints a message and exits 1. Live runs mean calling `run_trial` from your own script, as above.
- **Live adapters are not tested.** `AnthropicSDKClient`, `AzureOpenAISDKClient`, `AzureTranslatorSDKClient` and `OllamaHTTPClient` make real network calls and have no automated tests. Nothing in the 38 tests is skipped; the live adapters are simply outside the test suite.
- **No judge client is included.** `run_trial` takes a function that sends a prompt to a judge model and returns text. You supply it.
- **`comprehension_accuracy` is not computed.** The answer key is loaded but not yet scored.
- Google Sheets export needs a service-account JSON file and is untested against the real service.

## Licence

Apache-2.0. See [LICENSE](LICENSE).

Designed and authored by Daniel Boles; implemented with coding agents.
