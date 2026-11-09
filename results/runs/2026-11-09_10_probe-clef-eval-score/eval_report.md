# Decision eval eval-eabf1825ad45

- Provider: `clef-ollama` requesting `clef:cloud`; served {'clef': 1}; live: True
- Thresholds (placeholder, uncalibrated): yes >= 0.7, no <= 0.3; between is an abstention
- Items: 1; stopped early: no; outcomes {'ACCEPT': 1}
- Calls: 1 (transport retries 0); decision input tokens 554; provider errors: none
- Gold: by construction (corpus/decision_v1 generator); paraphrase items are author-written. False pass = the answer that lets work proceed when gold says it should not.

## Scored questions

| Scope | n | correct (acc) | decided acc | abstain | errors | Brier | false pass | over-refusal |
|---|---|---|---|---|---|---|---|---|
| `requirements_sufficient` | 1 | 1/1 (1.00) | 1.00 | 0 | 0 | 0.001 | 0/1 | 0/0 |

## Subset: kobayashi_maru

No-win items (gold: infeasible, premise false) and feasible near-misses (gold: feasible, premise true). A false pass here is a false 'feasible' / 'valid' call on a no-win item; an over-refusal is a false 'infeasible' / 'invalid' call on a near-miss.

| Scope | n | correct (acc) | decided acc | abstain | errors | Brier | false pass | over-refusal |
|---|---|---|---|---|---|---|---|---|

## By category

| Scope | n | correct (acc) | decided acc | abstain | errors | Brier | false pass | over-refusal |
|---|---|---|---|---|---|---|---|---|
| `requirements_sufficient` / missing | 1 | 1/1 (1.00) | 1.00 | 0 | 0 | 0.001 | 0/1 | 0/0 |

## By language

| Scope | n | correct (acc) | decided acc | abstain | errors | Brier | false pass | over-refusal |
|---|---|---|---|---|---|---|---|---|
| `requirements_sufficient` / en | 1 | 1/1 (1.00) | 1.00 | 0 | 0 | 0.001 | 0/1 | 0/0 |

## Confusion matrices (rows: gold; columns: verdict)

`requirements_sufficient`: gold yes {'yes': 0, 'no': 0, 'abstain': 0, 'error': 0}; gold no {'yes': 0, 'no': 1, 'abstain': 0, 'error': 0}

## Unreviewed: intervention_level (score)

No construction-based gold exists. Author estimates are author_unreviewed; agreement with them is not accuracy.

- `intervention_level`: 1/1 mapped answers; errors none; levels {'moderate': 1}; agrees with author estimate 0/1
- Raw score answer fields seen: {'confidence,legend,probabilities,score,type': 1}
- Example raw score answer: `{"type": "score", "score": 1.8865, "confidence": 0.5497, "legend": {"0": "none", "1": "minor", "2": "moderate", "3": "major"}, "probabilities": {"0": 0.0194, "1": 0.1266, "2": 0.802, "3": 0.052}}`
