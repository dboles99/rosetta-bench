# Decision run dec-77042fd7b6c3

> **SYNTHETIC: wiring check only.** The provider was an offline keyword-overlap fake, not a decision model. These figures are not evidence about Jev, clef or any provider.

- Provider: `fake` requesting `fake-systemone-1`; live: False
- Policy: `intake-placeholder` 0.1, calibrated: False, thresholds {'fit_yes': 0.7, 'fit_no': 0.3, 'route_default': 0.6}
- Question set hash: `7fcb77fc76dab360…`
- Cases: 32; stopped early: no
- Labels: authored for wiring, not independently reviewed. Smoke cases establish wiring, not performance.

## Outcomes

| Outcome | Count |
|---|---|
| ABSTAIN | 17 |
| ACCEPT | 4 |
| DENY | 1 |
| NO_FIT | 10 |

## Decision quality

- Top-1 route choice vs label (fits cases with an eligible labelled route, ignoring thresholds): 15/19 (79%)
- Brier score of `route_fits` vs label: 0.2353 over 31 cases
- Accepted routes matching the label: 4/4 (100%)
- Coverage (ACCEPT among labelled-fit cases): 4/20 (20%)
- No-fit recall (NO_FIT among labelled no-fit cases): 6/11 (55%)
- False accepts on no-fit cases: 0/11 (0%)
- Abstentions: 17; fallbacks: 0

## By category

| Category | Cases | ACCEPT | correct ACCEPT | NO_FIT | ABSTAIN | FALLBACK | DENY |
|---|---|---|---|---|---|---|---|
| adversarial | 2 | 0 | 0 | 0 | 2 | 0 | 0 |
| ambiguous | 10 | 0 | 0 | 3 | 7 | 0 | 0 |
| gate | 2 | 0 | 0 | 0 | 1 | 0 | 1 |
| no_fit | 8 | 0 | 0 | 6 | 2 | 0 | 0 |
| obvious | 10 | 4 | 4 | 1 | 5 | 0 | 0 |

## By language

| Language | Cases | correct ACCEPT | NO_FIT |
|---|---|---|---|
| en | 24 | 3 | 7 |
| ja | 2 | 0 | 1 |
| mixed | 4 | 1 | 0 |
| zh | 2 | 0 | 2 |

## Economics and reliability

- Provider calls: 31; transport retries: 0
- Decision input tokens: 9361 over 31 answered cases
- Decision latency p50 / p95 ms: 0.44380000326782465 / 0.5506000015884638
- Provider errors: none
- Validation violations: 0
