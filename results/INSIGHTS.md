# Insights from the runs of 2026-11-09

Mined from `results/runs/` via `results/rosetta_bench.sqlite` (rebuild with `bench results db`). Every figure below names
its source run. These are leads from small samples (one temperature-0 generation per prompt, 18-32 tasks, author or
by-construction labels, uncalibrated thresholds), not findings. Status of each follow-up is tracked at the end.

## 1. The plain prompt's extra cost is hidden reasoning, not extra text

Source: `2026-11-09_09_usefulness-matrix-live`, unique code generations, `kimi-k2.7-code:cloud`.

| Representation | Mean output tokens per code task | Visible characters per output token |
|---|---|---|
| P plain prose | 1,610 | 0.6 |
| M Rosetta `.cpn` | 742 | 1.0 |
| H Rosetta `.md` | 568 | 1.4 |

Visible replies were about the same length in every representation (roughly 400-500 characters of code), so the extra
output tokens were not visible prose. The worst case, P on u05, reported 6,294 output tokens for 400 characters of code
and took 45 s. The runner keeps only the visible reply, so "hidden reasoning" is inferred from the token counts. H costs
more input (388 tokens vs 150 for M) but was followed by the least reasoning.

## 2. A decision call is about 95% fixed overhead

Source: same run, `decisions.jsonl`. Fitted input tokens per intake call:
clef ≈ 670 + 0.20 per request character; Jev ≈ 850 + 0.19 per request character. The question instructions and the
route catalogue dominate. Jev's tokenizer counts about 27% more than clef's for identical input.

## 3. Intake routing cannot pay for itself on this task mix

Source: same run. A decline saves only what the baseline would have spent on a no-code request: 58-143 generator tokens,
because the baseline contract already answers `NOT_A_CODE_TASK`. A decision costs 707 (clef) or 885 (Jev) tokens per
task. With one request in three being no-code, a declined request would have to cost at least about 2,100 (clef) or
2,700 (Jev) generator tokens to break even. Routing belongs in front of expensive work (long context, multi-step
agents) or traffic that is mostly out of scope.

## 4. Consensus doubles the cost for little information

Source: `2026-11-09_07` and `_08` (smoke, question set 1.1). Jev and clef `route_fits` probabilities correlate at 0.97.
Clef was cheaper (671 vs 844 tokens per call) and faster (0.93 s vs 1.43 s). Consensus pays both every time.

## 5. Wording is part of the calibration

Source: `2026-11-09_04` vs `_07`. Rewording route_fits (question set 1.0 to 1.1, same meaning) moved Jev's probability by
0.042 on average and up to 0.17; 5 of 31 cases moved more than 0.1, enough to cross the 0.7 threshold. Thresholds are
valid only for the exact wording they were calibrated on.

## 6. Clef's uncertainty is informative

Source: `2026-11-09_11_decision-eval-clef` (142 by-construction items). Correct answers sat a mean 0.46 away from 0.5; all
8 misses sat within a mean 0.09 of 0.5 and were caught as abstentions, with no false passes and no over-refusals. Half
the misses were Japanese near-miss items; noul accuracy was 98.5% en, 95.7% zh, 88.4% ja. Every miss was a feasible or
valid near-miss needing a boundary or arithmetic check.

## 7. Postflight is untested so far

Source: `2026-11-09_09`. All generated code passed, so there was no failure to detect. Clef raised one false alarm
(p = 0.47 on correct u11); Jev's lowest score was 0.71. The harder corpus is needed to measure discrimination.

## 8. Sharing identical prompts saved two-thirds of generator calls

Source: `2026-11-09_09`. 54 unique generations served 162 charged arm-trials.

## Follow-ups

| # | Improvement | Status |
|---|---|---|
| 1 | Record reasoning tokens separately; test a reasoning cap / thinking off | planned after the hard-problems merge |
| 2 | Replicate P vs M with 3-5 samples per prompt at temperature > 0 | planned |
| 3 | Shrink decision overhead (route catalogue as a compact Rosetta packet, shorter questions), then recalibrate | planned |
| 4 | Use intake only where it can pay (expensive downstream work, ambiguous requests) | design note |
| 5 | Cascade instead of consensus: ask a second provider only when the first is uncertain | design note |
| 6 | Calibrate abstain bands per question and language on a held-out split; more Japanese items | needs gold labels and splits |
| 7 | Evaluate postflight on the harder corpus, which contains failing code | depends on the hard-problems branch |
| 8 | Notebook: intervals, reasoning-token view, decision-eval section, per-task drill-down, USD cost where known | planned |
| 9 | Bug: usefulness receipts record transport retries as 0 instead of the real count | planned |
