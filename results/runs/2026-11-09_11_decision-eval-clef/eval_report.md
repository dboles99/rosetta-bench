# Decision eval eval-513daa088ed3

- Provider: `clef-ollama` requesting `clef:cloud`; served {'clef': 142}; live: True
- Thresholds (placeholder, uncalibrated): yes >= 0.7, no <= 0.3; between is an abstention
- Items: 142; stopped early: no; outcomes {'ACCEPT': 136, 'ABSTAIN': 6}
- Calls: 142 (transport retries 0); decision input tokens 71,064; provider errors: none
- Gold: by construction (corpus/decision_v1 generator); paraphrase items are author-written. False pass = the answer that lets work proceed when gold says it should not.

## Scored questions

| Scope | n | correct (acc) | decided acc | abstain | errors | Brier | false pass | over-refusal |
|---|---|---|---|---|---|---|---|---|
| `meaning_changed` | 20 | 20/20 (1.00) | 1.00 | 0 | 0 | 0.000 | 0/10 | 0/10 |
| `notes_consistent` (Rosetta execution) | 20 | 20/20 (1.00) | 1.00 | 0 | 0 | 0.001 | 0/10 | 0/10 |
| `output_supported` | 20 | 20/20 (1.00) | 1.00 | 0 | 0 | 0.000 | 0/10 | 0/10 |
| `premise_valid` | 32 | 27/32 (0.84) | 1.00 | 5 | 0 | 0.043 | 0/16 | 0/16 |
| `requirements_sufficient` | 20 | 20/20 (1.00) | 1.00 | 0 | 0 | 0.007 | 0/10 | 0/10 |
| `task_feasible` | 22 | 19/22 (0.86) | 1.00 | 3 | 0 | 0.058 | 0/11 | 0/11 |
| `views_equivalent` (Rosetta execution) | 20 | 20/20 (1.00) | 1.00 | 0 | 0 | 0.000 | 0/10 | 0/10 |

## Subset: kobayashi_maru

No-win items (gold: infeasible, premise false) and feasible near-misses (gold: feasible, premise true). A false pass here is a false 'feasible' / 'valid' call on a no-win item; an over-refusal is a false 'infeasible' / 'invalid' call on a near-miss.

| Scope | n | correct (acc) | decided acc | abstain | errors | Brier | false pass | over-refusal |
|---|---|---|---|---|---|---|---|---|
| `task_feasible` in subset | 12 | 10/12 (0.83) | 1.00 | 2 | 0 | 0.072 | 0/6 | 0/6 |
| `task_feasible` outside subset | 10 | 9/10 (0.90) | 1.00 | 1 | 0 | 0.042 | 0/5 | 0/5 |
| `premise_valid` in subset | 12 | 7/12 (0.58) | 1.00 | 5 | 0 | 0.112 | 0/6 | 0/6 |
| `premise_valid` outside subset | 20 | 20/20 (1.00) | 1.00 | 0 | 0 | 0.002 | 0/10 | 0/10 |

## By category

| Scope | n | correct (acc) | decided acc | abstain | errors | Brier | false pass | over-refusal |
|---|---|---|---|---|---|---|---|---|
| `meaning_changed` / hedge | 3 | 3/3 (1.00) | 1.00 | 0 | 0 | 0.001 | 0/3 | 0/0 |
| `meaning_changed` / negation | 3 | 3/3 (1.00) | 1.00 | 0 | 0 | 0.000 | 0/3 | 0/0 |
| `meaning_changed` / number | 4 | 4/4 (1.00) | 1.00 | 0 | 0 | 0.000 | 0/4 | 0/0 |
| `meaning_changed` / paraphrase | 10 | 10/10 (1.00) | 1.00 | 0 | 0 | 0.000 | 0/0 | 0/10 |
| `notes_consistent` / corrupted | 10 | 10/10 (1.00) | 1.00 | 0 | 0 | 0.002 | 0/10 | 0/0 |
| `notes_consistent` / faithful | 10 | 10/10 (1.00) | 1.00 | 0 | 0 | 0.000 | 0/0 | 0/10 |
| `output_supported` / contradicted | 2 | 2/2 (1.00) | 1.00 | 0 | 0 | 0.000 | 0/2 | 0/0 |
| `output_supported` / not_mentioned | 4 | 4/4 (1.00) | 1.00 | 0 | 0 | 0.000 | 0/4 | 0/0 |
| `output_supported` / number_altered | 4 | 4/4 (1.00) | 1.00 | 0 | 0 | 0.000 | 0/4 | 0/0 |
| `output_supported` / supported | 10 | 10/10 (1.00) | 1.00 | 0 | 0 | 0.001 | 0/0 | 0/10 |
| `premise_valid` / code_bug | 6 | 6/6 (1.00) | 1.00 | 0 | 0 | 0.006 | 0/3 | 0/3 |
| `premise_valid` / document | 2 | 2/2 (1.00) | 1.00 | 0 | 0 | 0.001 | 0/1 | 0/1 |
| `premise_valid` / near_miss | 6 | 1/6 (0.17) | 1.00 | 5 | 0 | 0.216 | 0/0 | 0/6 |
| `premise_valid` / no_win | 6 | 6/6 (1.00) | 1.00 | 0 | 0 | 0.007 | 0/6 | 0/0 |
| `premise_valid` / rosetta_loader | 2 | 2/2 (1.00) | 1.00 | 0 | 0 | 0.000 | 0/1 | 0/1 |
| `premise_valid` / rosetta_notes | 4 | 4/4 (1.00) | 1.00 | 0 | 0 | 0.000 | 0/2 | 0/2 |
| `premise_valid` / rosetta_packet | 4 | 4/4 (1.00) | 1.00 | 0 | 0 | 0.000 | 0/2 | 0/2 |
| `premise_valid` / rosetta_sync | 2 | 2/2 (1.00) | 1.00 | 0 | 0 | 0.000 | 0/1 | 0/1 |
| `requirements_sufficient` / complete | 10 | 10/10 (1.00) | 1.00 | 0 | 0 | 0.007 | 0/0 | 0/10 |
| `requirements_sufficient` / missing | 10 | 10/10 (1.00) | 1.00 | 0 | 0 | 0.006 | 0/10 | 0/0 |
| `task_feasible` / contradiction | 2 | 2/2 (1.00) | 1.00 | 0 | 0 | 0.000 | 0/2 | 0/0 |
| `task_feasible` / feasible | 5 | 4/5 (0.80) | 1.00 | 1 | 0 | 0.080 | 0/0 | 0/5 |
| `task_feasible` / impossible | 2 | 2/2 (1.00) | 1.00 | 0 | 0 | 0.006 | 0/2 | 0/0 |
| `task_feasible` / missing_information | 1 | 1/1 (1.00) | 1.00 | 0 | 0 | 0.004 | 0/1 | 0/0 |
| `task_feasible` / near_miss | 6 | 4/6 (0.67) | 1.00 | 2 | 0 | 0.128 | 0/0 | 0/6 |
| `task_feasible` / no_win | 6 | 6/6 (1.00) | 1.00 | 0 | 0 | 0.016 | 0/6 | 0/0 |
| `views_equivalent` / changed-cpn | 6 | 6/6 (1.00) | 1.00 | 0 | 0 | 0.000 | 0/6 | 0/0 |
| `views_equivalent` / changed-md | 4 | 4/4 (1.00) | 1.00 | 0 | 0 | 0.001 | 0/4 | 0/0 |
| `views_equivalent` / equal-md | 5 | 5/5 (1.00) | 1.00 | 0 | 0 | 0.000 | 0/0 | 0/5 |
| `views_equivalent` / equal-reorder | 5 | 5/5 (1.00) | 1.00 | 0 | 0 | 0.000 | 0/0 | 0/5 |

## By language

| Scope | n | correct (acc) | decided acc | abstain | errors | Brier | false pass | over-refusal |
|---|---|---|---|---|---|---|---|---|
| `meaning_changed` / en | 8 | 8/8 (1.00) | 1.00 | 0 | 0 | 0.000 | 0/4 | 0/4 |
| `meaning_changed` / ja | 6 | 6/6 (1.00) | 1.00 | 0 | 0 | 0.000 | 0/3 | 0/3 |
| `meaning_changed` / zh | 6 | 6/6 (1.00) | 1.00 | 0 | 0 | 0.000 | 0/3 | 0/3 |
| `notes_consistent` / en | 8 | 8/8 (1.00) | 1.00 | 0 | 0 | 0.001 | 0/4 | 0/4 |
| `notes_consistent` / ja | 6 | 6/6 (1.00) | 1.00 | 0 | 0 | 0.001 | 0/3 | 0/3 |
| `notes_consistent` / zh | 6 | 6/6 (1.00) | 1.00 | 0 | 0 | 0.001 | 0/3 | 0/3 |
| `output_supported` / en | 8 | 8/8 (1.00) | 1.00 | 0 | 0 | 0.000 | 0/4 | 0/4 |
| `output_supported` / ja | 6 | 6/6 (1.00) | 1.00 | 0 | 0 | 0.001 | 0/3 | 0/3 |
| `output_supported` / zh | 6 | 6/6 (1.00) | 1.00 | 0 | 0 | 0.000 | 0/3 | 0/3 |
| `premise_valid` / en | 14 | 13/14 (0.93) | 1.00 | 1 | 0 | 0.009 | 0/7 | 0/7 |
| `premise_valid` / ja | 8 | 6/8 (0.75) | 1.00 | 2 | 0 | 0.096 | 0/4 | 0/4 |
| `premise_valid` / zh | 10 | 8/10 (0.80) | 1.00 | 2 | 0 | 0.048 | 0/5 | 0/5 |
| `requirements_sufficient` / en | 8 | 8/8 (1.00) | 1.00 | 0 | 0 | 0.006 | 0/4 | 0/4 |
| `requirements_sufficient` / ja | 6 | 6/6 (1.00) | 1.00 | 0 | 0 | 0.011 | 0/3 | 0/3 |
| `requirements_sufficient` / zh | 6 | 6/6 (1.00) | 1.00 | 0 | 0 | 0.004 | 0/3 | 0/3 |
| `task_feasible` / en | 9 | 9/9 (1.00) | 1.00 | 0 | 0 | 0.009 | 0/5 | 0/4 |
| `task_feasible` / ja | 7 | 4/7 (0.57) | 1.00 | 3 | 0 | 0.148 | 0/3 | 0/4 |
| `task_feasible` / zh | 6 | 6/6 (1.00) | 1.00 | 0 | 0 | 0.028 | 0/3 | 0/3 |
| `views_equivalent` / en | 10 | 10/10 (1.00) | 1.00 | 0 | 0 | 0.000 | 0/5 | 0/5 |
| `views_equivalent` / ja | 4 | 4/4 (1.00) | 1.00 | 0 | 0 | 0.001 | 0/2 | 0/2 |
| `views_equivalent` / zh | 6 | 6/6 (1.00) | 1.00 | 0 | 0 | 0.000 | 0/3 | 0/3 |

## Confusion matrices (rows: gold; columns: verdict)

`meaning_changed`: gold yes {'yes': 10, 'no': 0, 'abstain': 0, 'error': 0}; gold no {'yes': 0, 'no': 10, 'abstain': 0, 'error': 0}
`notes_consistent`: gold yes {'yes': 10, 'no': 0, 'abstain': 0, 'error': 0}; gold no {'yes': 0, 'no': 10, 'abstain': 0, 'error': 0}
`output_supported`: gold yes {'yes': 10, 'no': 0, 'abstain': 0, 'error': 0}; gold no {'yes': 0, 'no': 10, 'abstain': 0, 'error': 0}
`premise_valid`: gold yes {'yes': 11, 'no': 0, 'abstain': 5, 'error': 0}; gold no {'yes': 0, 'no': 16, 'abstain': 0, 'error': 0}
`requirements_sufficient`: gold yes {'yes': 10, 'no': 0, 'abstain': 0, 'error': 0}; gold no {'yes': 0, 'no': 10, 'abstain': 0, 'error': 0}
`task_feasible`: gold yes {'yes': 8, 'no': 0, 'abstain': 3, 'error': 0}; gold no {'yes': 0, 'no': 11, 'abstain': 0, 'error': 0}
`views_equivalent`: gold yes {'yes': 10, 'no': 0, 'abstain': 0, 'error': 0}; gold no {'yes': 0, 'no': 10, 'abstain': 0, 'error': 0}

## Unreviewed: intervention_level (score)

No construction-based gold exists. Author estimates are author_unreviewed; agreement with them is not accuracy.

- `intervention_level`: 20/20 mapped answers; errors none; levels {'moderate': 10, 'none': 6, 'minor': 4}; agrees with author estimate 6/20
- Raw score answer fields seen: {'confidence,legend,probabilities,score,type': 20}
- Example raw score answer: `{"type": "score", "score": 1.853, "confidence": 0.3809, "legend": {"0": "none", "1": "minor", "2": "moderate", "3": "major"}, "probabilities": {"0": 0.0305, "1": 0.1756, "2": 0.7042, "3": 0.0897}}`
