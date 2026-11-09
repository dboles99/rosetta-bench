# Decision eval eval-686017033df2

- Provider: `jevmodel` requesting `jev-latest`; served {'jev-1.14.0': 30}; live: True
- Thresholds (placeholder, uncalibrated): yes >= 0.7, no <= 0.3; between is an abstention
- Items: 30; stopped early: no; outcomes {'ACCEPT': 25, 'ABSTAIN': 5}
- Calls: 30 (transport retries 0); decision input tokens 21,284; provider errors: none
- Gold: by construction (corpus/decision_v1 generator); paraphrase items are author-written. False pass = the answer that lets work proceed when gold says it should not.

## Scored questions

| Scope | n | correct (acc) | decided acc | abstain | errors | Brier | false pass | over-refusal |
|---|---|---|---|---|---|---|---|---|
| `premise_valid` | 20 | 17/20 (0.85) | 0.94 | 2 | 0 | 0.072 | 1/10 | 0/10 |
| `task_feasible` | 22 | 14/22 (0.64) | 0.82 | 5 | 0 | 0.151 | 1/11 | 2/11 |

## Subset: kobayashi_maru

No-win items (gold: infeasible, premise false) and feasible near-misses (gold: feasible, premise true). A false pass here is a false 'feasible' / 'valid' call on a no-win item; an over-refusal is a false 'infeasible' / 'invalid' call on a near-miss.

| Scope | n | correct (acc) | decided acc | abstain | errors | Brier | false pass | over-refusal |
|---|---|---|---|---|---|---|---|---|
| `task_feasible` in subset | 12 | 9/12 (0.75) | 0.90 | 2 | 0 | 0.110 | 1/6 | 0/6 |
| `task_feasible` outside subset | 10 | 5/10 (0.50) | 0.71 | 3 | 0 | 0.200 | 0/5 | 2/5 |
| `premise_valid` in subset | 12 | 9/12 (0.75) | 0.90 | 2 | 0 | 0.108 | 1/6 | 0/6 |
| `premise_valid` outside subset | 8 | 8/8 (1.00) | 1.00 | 0 | 0 | 0.018 | 0/4 | 0/4 |

## By category

| Scope | n | correct (acc) | decided acc | abstain | errors | Brier | false pass | over-refusal |
|---|---|---|---|---|---|---|---|---|
| `premise_valid` / code_bug | 6 | 6/6 (1.00) | 1.00 | 0 | 0 | 0.021 | 0/3 | 0/3 |
| `premise_valid` / near_miss | 6 | 4/6 (0.67) | 1.00 | 2 | 0 | 0.094 | 0/0 | 0/6 |
| `premise_valid` / no_win | 6 | 5/6 (0.83) | 0.83 | 0 | 0 | 0.122 | 1/6 | 0/0 |
| `premise_valid` / rosetta_sync | 2 | 2/2 (1.00) | 1.00 | 0 | 0 | 0.012 | 0/1 | 0/1 |
| `task_feasible` / contradiction | 2 | 2/2 (1.00) | 1.00 | 0 | 0 | 0.006 | 0/2 | 0/0 |
| `task_feasible` / feasible | 5 | 1/5 (0.20) | 0.33 | 2 | 0 | 0.362 | 0/0 | 2/5 |
| `task_feasible` / impossible | 2 | 1/2 (0.50) | 1.00 | 1 | 0 | 0.085 | 0/2 | 0/0 |
| `task_feasible` / missing_information | 1 | 1/1 (1.00) | 1.00 | 0 | 0 | 0.006 | 0/1 | 0/0 |
| `task_feasible` / near_miss | 6 | 4/6 (0.67) | 1.00 | 2 | 0 | 0.076 | 0/0 | 0/6 |
| `task_feasible` / no_win | 6 | 5/6 (0.83) | 0.83 | 0 | 0 | 0.143 | 1/6 | 0/0 |

## By language

| Scope | n | correct (acc) | decided acc | abstain | errors | Brier | false pass | over-refusal |
|---|---|---|---|---|---|---|---|---|
| `premise_valid` / en | 8 | 7/8 (0.88) | 1.00 | 1 | 0 | 0.025 | 0/4 | 0/4 |
| `premise_valid` / ja | 6 | 5/6 (0.83) | 0.83 | 0 | 0 | 0.117 | 1/3 | 0/3 |
| `premise_valid` / zh | 6 | 5/6 (0.83) | 1.00 | 1 | 0 | 0.090 | 0/3 | 0/3 |
| `task_feasible` / en | 9 | 6/9 (0.67) | 0.75 | 1 | 0 | 0.164 | 0/5 | 2/4 |
| `task_feasible` / ja | 7 | 3/7 (0.43) | 0.75 | 3 | 0 | 0.204 | 1/3 | 0/4 |
| `task_feasible` / zh | 6 | 5/6 (0.83) | 1.00 | 1 | 0 | 0.069 | 0/3 | 0/3 |

## Confusion matrices (rows: gold; columns: verdict)

`premise_valid`: gold yes {'yes': 8, 'no': 0, 'abstain': 2, 'error': 0}; gold no {'yes': 1, 'no': 9, 'abstain': 0, 'error': 0}
`task_feasible`: gold yes {'yes': 5, 'no': 2, 'abstain': 4, 'error': 0}; gold no {'yes': 1, 'no': 9, 'abstain': 1, 'error': 0}

## Unreviewed: intervention_level (score)

No construction-based gold exists. Author estimates are author_unreviewed; agreement with them is not accuracy.

- Raw score answer fields seen: none
- No raw score answer recorded
