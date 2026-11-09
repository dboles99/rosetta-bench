# Decision run dec-7ac558a8b554

- Provider: `clef-ollama` requesting `clef:cloud`; live: True
- Policy: `intake-placeholder` 0.1, calibrated: False, thresholds {'fit_yes': 0.7, 'fit_no': 0.3, 'route_default': 0.6}
- Question set hash: `2ee55fc0d3c86608…`
- Cases: 32; stopped early: no
- Cache: off
- Batching: 4 requests per call (question set 2.0, separate calibration needed)
- Labels: authored for wiring, not independently reviewed. Smoke cases establish wiring, not performance.

## Outcomes

| Outcome | Count |
|---|---|
| ABSTAIN | 8 |
| ACCEPT | 13 |
| DENY | 1 |
| NO_FIT | 10 |

## Decision quality

- Top-1 route choice vs label (fits cases with an eligible labelled route, ignoring thresholds): 16/19 (84%)
- Brier score of `route_fits` vs label: 0.0367 over 31 cases
- Accepted routes matching the label: 13/13 (100%)
- Coverage (ACCEPT among labelled-fit cases): 13/20 (65%)
- No-fit recall (NO_FIT among labelled no-fit cases): 10/11 (91%)
- False accepts on no-fit cases: 0/11 (0%)
- Abstentions: 8; fallbacks: 0

## By category

| Category | Cases | ACCEPT | correct ACCEPT | NO_FIT | ABSTAIN | FALLBACK | DENY |
|---|---|---|---|---|---|---|---|
| adversarial | 2 | 0 | 0 | 2 | 0 | 0 | 0 |
| ambiguous | 10 | 3 | 3 | 0 | 7 | 0 | 0 |
| gate | 2 | 0 | 0 | 0 | 1 | 0 | 1 |
| no_fit | 8 | 0 | 0 | 8 | 0 | 0 | 0 |
| obvious | 10 | 10 | 10 | 0 | 0 | 0 | 0 |

## By language

| Language | Cases | correct ACCEPT | NO_FIT |
|---|---|---|---|
| en | 24 | 9 | 8 |
| ja | 2 | 1 | 1 |
| mixed | 4 | 2 | 0 |
| zh | 2 | 1 | 1 |

## Economics and reliability

- Provider calls: 8; transport retries: 0
- Decision input tokens: 17456 over 31 answered cases
- Decision latency p50 / p95 ms: 621.5704999631271 / 946.212800045032
- Provider errors: none
- Validation violations: 0
