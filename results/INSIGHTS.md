# Insights from the runs of 2026-11-09

Mined from `results/runs/` via `results/rosetta_bench.sqlite` (rebuild with `bench results db`). Every figure below names
its source run. These are leads from small samples (insights 1-8: one temperature-0 generation per prompt, 18-32 tasks;
insights 9-10: 3 samples per arm on 66 tasks; author or by-construction labels; uncalibrated thresholds), not findings.
Status of each follow-up is tracked at the end.

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

## 9. Thinking is what refuses impossible work

Sources: runs `_18`/`_24`/`_27` (M, thinking on) vs `_19`/`_25`/`_28` (M, thinking off); usefulness_v2, 66 tasks, 3
samples per arm (temperature 0, then 0.6 with seeds 20261110 and 20261111), pooled in `results/COMPARISON_3x3.md`.
Accuracy 0.899 vs 0.626 (difference 0.273, 95% CI 0.172 to 0.374; majority McNemar p < 0.001). The gap is in the honest
outcomes: unsolvable 24/24 vs 7/24, false premise 11/18 vs 0/18; code 87/99 vs 68/99. Thinking costs about 11 times the
output tokens (211k vs 19k per run) and 3.4 times the tokens per verified success (4,041 vs 1,179). Sample-to-sample
spread is real: thinking on scored 57, 61 and 60 of 66.

## 10. Reason-first moves the honesty into a cheap plan, but not the code quality

Sources: runs `_23`/`_26`/`_29` (R, plan schema 1.1: planner thinking on, executor thinking off). Accuracy 0.778, between
the two plain arms: unsolvable 21/24 and false premise 9/18 (close to thinking on), but code 74/99 (closer to thinking off,
68/99). The planner said PROCEED on 8 of the 18 false-premise trials. Against thinking on: 0.121 lower (95% CI 0.051 to
0.192; majority McNemar p = 0.109), 45% fewer output tokens (115k vs 211k per run) but only 11% fewer tokens per verified
success (3,584 vs 4,041), p95 latency 42 s vs 146 s, 2 timeouts vs 5. The arms do not tie, so the approved Rust port
(conditional on a tie) was not started.

## 11. An offline fake that is kinder than the live model hides defects

Source: run `_20` (R, plan schema 1.0): 34/66, with 0/14 on clarify, data_query, docs_edit and translation_review. The
live planner labelled those NOT_A_CODE_TASK and the pipeline returned the bare label; the fake planner sent them to
PROCEED, so no offline test reached that path. Fixed in `7c8c174` (hand-off verdicts, NEEDS_CLARIFICATION, fake planner
mirrors the live one). Run `_23` repeats `_20` with the fix: 52/66, 13/14 on those kinds.

## 12. Paraphrase ensembles add nothing over the single answer's margin

Source: `2026-11-09_22_decision-eval-clef-paraphrase` (142 items, 3 wordings per yes/no question in one call). Accuracy:
single wording 0.93, mean of three 0.89, majority 0.93. As an error signal, spread across wordings has AUROC 0.68 (0.92
on the two wordings that held up), against 0.99 for the single answer's distance from 0.5. Two of the seven new wordings
broke on well-answered items: "do the views disagree?" came back reversed on 17/20, "is anything missing?" scored 10/20.
Two other negatively framed wordings were 20/20, so the failure is not predictable from polarity. Consequence: never
reword a pinned question without re-running it against gold; the content-hash pins already enforce that.

## 13. Calibrated abstention cannot certify anything yet

Source: `bench decision calibrate` on `2026-11-09_11_decision-eval-clef`. With about 11 items per question and side, no
threshold certifies a false-pass rate of 10% at 90% confidence (Clopper-Pearson with a Bonferroni grid needs about 27
correct answers with no error on a side), so every question stays at "always abstain". About 60 items per question are
needed; the routing_v1 labels are the next source.

## 14. Jev and clef differ by question, not overall

Source: `2026-11-09_21_decision-eval-jevmodel-subset` (30 items, last free Jev tokens, 21,284 tokens). Feasibility 14/22
(Jev) vs 19/22 (clef); premise 17/20 vs 15/20. Jev gave one confident false pass (km-ja-01-no-win). Too small to rank them.

## 15. Caching removes the decision cost on repeats; compact wording beats batching

Sources: `_13` (cache warm: 0 calls, 0 tokens on a repeated run), `_15` (intake 1.2 compact wording: 14% fewer tokens,
accuracy equal or better), `_14` (batches of 4: only 16% fewer tokens because the route list was repeated per slot, and
accuracy fell; rejected).

## Follow-ups

| # | Improvement | Status |
|---|---|---|
| 1 | Record reasoning tokens separately; test a reasoning cap / thinking off | done: insight 9 (cap not tested) |
| 2 | Replicate with 3-5 samples per prompt at temperature > 0 | done for M thinking on/off and R (3 each); P vs M still single-sample |
| 3 | Shrink decision overhead (route catalogue as a compact Rosetta packet, shorter questions), then recalibrate | done: compact 1.2 (insight 15) |
| 4 | Use intake only where it can pay (expensive downstream work, ambiguous requests) | design note |
| 5 | Cascade instead of consensus: ask a second provider only when the first is uncertain | design note |
| 6 | Calibrate abstain bands per question and language on a held-out split; more Japanese items | tool built (`bench decision calibrate`); needs about 60 labelled items per question |
| 7 | Evaluate postflight on the harder corpus, which contains failing code | open |
| 8 | Notebook: intervals, reasoning-token view, decision-eval section, per-task drill-down, USD cost where known | in progress |
| 9 | Bug: usefulness receipts record transport retries as 0 instead of the real count | fixed in `cf638e2` |
| 10 | Detecting a 5-point difference between arms needs about 500-1,000 tasks; the corpus has 66 | open: grow the corpus before claiming ties |
| 11 | Reason-first loses on code: try executor thinking on for code plans only, or a cheaper thinking budget | candidate |
| 12 | Reason-first lets 8/18 false premises through: gate PROCEED plans with clef `premise_valid` (15/20 on the subset) | candidate; test on usefulness_v3, which also has the 4 REPORT_DEFECT tasks |
| 13 | Paraphrase ensembles | rejected as a signal (insight 12); kept as a wording-robustness check |
