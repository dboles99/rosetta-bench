# Run run-0609dfc6a525: smoke-offline

> **SYNTHETIC: wiring check only.** Every arm used an offline fake generator. These numbers describe the corpus files and the scorers, not any model, and are not evidence for any claim.

- Cases: 1 (the unit of paired resampling)
- Trials: 4; seed 20261109; repeats 1 (repeats are not new cases)
- Bench repo: {'sha': '2ebf2726d31a5fecf34a3f8dd3762ac65a7f1e57', 'dirty': True}

## Per arm and suite

| Arm | Suite | Format | n | Errors | Comprehension accuracy | Task success | Mean tokens in | Mean tokens out | p50 generation ms | p95 generation ms | Cost USD (known) | Unknown-cost trials |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | COMPREHENSION | HUMAN | 1 | 0 | 1.000 | – | 233.0 | 10.0 | 0.2 | 0.2 | 0.0000 | 0 |
| A | TASK_COMPLETION | HUMAN | 1 | 0 | – | 1/1 | 168.0 | 9.0 | 0.1 | 0.1 | 0.0000 | 0 |
| B | COMPREHENSION | MACHINE | 1 | 0 | 1.000 | – | 72.0 | 10.0 | 0.1 | 0.1 | 0.0000 | 0 |
| B | TASK_COMPLETION | MACHINE | 1 | 0 | – | 1/1 | 7.0 | 9.0 | 0.1 | 0.1 | 0.0000 | 0 |

## Paired by case, relative to arm A

| Arm | Suite | Cases | Mean difference | Interval |
|---|---|---|---|---|
| B | COMPREHENSION | 1 | 0.000 | not estimated (fewer than 10 cases) |
| B | TASK_COMPLETION | 1 | 0.000 | not estimated (fewer than 10 cases) |
