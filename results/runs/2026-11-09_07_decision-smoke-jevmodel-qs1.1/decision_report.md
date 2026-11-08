# Decision run dec-2d2e1f1d2b13

- Provider: `jevmodel` requesting `jev-latest`; live: True
- Policy: `intake-placeholder` 0.1, calibrated: False, thresholds {'fit_yes': 0.7, 'fit_no': 0.3, 'route_default': 0.6}
- Question set hash: `2ee55fc0d3c86608…`
- Cases: 32; stopped early: no
- Labels: authored for wiring, not independently reviewed. Smoke cases establish wiring, not performance.

## Outcomes

| Outcome | Count |
|---|---|
| ABSTAIN | 4 |
| ACCEPT | 17 |
| DENY | 1 |
| NO_FIT | 10 |

## Decision quality

- Top-1 route choice vs label (fits cases with an eligible labelled route, ignoring thresholds): 19/19 (100%)
- Brier score of `route_fits` vs label: 0.0321 over 31 cases
- Accepted routes matching the label: 17/17 (100%)
- Coverage (ACCEPT among labelled-fit cases): 17/20 (85%)
- No-fit recall (NO_FIT among labelled no-fit cases): 10/11 (91%)
- False accepts on no-fit cases: 0/11 (0%)
- Abstentions: 4; fallbacks: 0

## By category

| Category | Cases | ACCEPT | correct ACCEPT | NO_FIT | ABSTAIN | FALLBACK | DENY |
|---|---|---|---|---|---|---|---|
| adversarial | 2 | 0 | 0 | 2 | 0 | 0 | 0 |
| ambiguous | 10 | 8 | 8 | 0 | 2 | 0 | 0 |
| gate | 2 | 0 | 0 | 0 | 1 | 0 | 1 |
| no_fit | 8 | 0 | 0 | 8 | 0 | 0 | 0 |
| obvious | 10 | 9 | 9 | 0 | 1 | 0 | 0 |

## By language

| Language | Cases | correct ACCEPT | NO_FIT |
|---|---|---|---|
| en | 24 | 12 | 8 |
| ja | 2 | 1 | 1 |
| mixed | 4 | 3 | 0 |
| zh | 2 | 1 | 1 |

## Economics and reliability

- Provider calls: 31; transport retries: 0
- Decision input tokens: 26178 over 31 answered cases
- Decision latency p50 / p95 ms: 1376.905800017994 / 1823.6037999740802
- Provider errors: none
- Validation violations: 0
