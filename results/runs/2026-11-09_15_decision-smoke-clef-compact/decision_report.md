# Decision run dec-8164fc83d3e6

- Provider: `clef-ollama` requesting `clef:cloud`; live: True
- Policy: `intake-placeholder` 0.1, calibrated: False, thresholds {'fit_yes': 0.7, 'fit_no': 0.3, 'route_default': 0.6}
- Question set hash: `83f2be1701202266…`
- Cases: 32; stopped early: no
- Cache: off
- Batching: off (one request per call)
- Labels: authored for wiring, not independently reviewed. Smoke cases establish wiring, not performance.

## Outcomes

| Outcome | Count |
|---|---|
| ABSTAIN | 3 |
| ACCEPT | 18 |
| DENY | 1 |
| NO_FIT | 10 |

## Decision quality

- Top-1 route choice vs label (fits cases with an eligible labelled route, ignoring thresholds): 18/19 (95%)
- Brier score of `route_fits` vs label: 0.0203 over 31 cases
- Accepted routes matching the label: 17/18 (94%)
- Coverage (ACCEPT among labelled-fit cases): 18/20 (90%)
- No-fit recall (NO_FIT among labelled no-fit cases): 10/11 (91%)
- False accepts on no-fit cases: 0/11 (0%)
- Abstentions: 3; fallbacks: 0

## By category

| Category | Cases | ACCEPT | correct ACCEPT | NO_FIT | ABSTAIN | FALLBACK | DENY |
|---|---|---|---|---|---|---|---|
| adversarial | 2 | 0 | 0 | 2 | 0 | 0 | 0 |
| ambiguous | 10 | 8 | 7 | 0 | 2 | 0 | 0 |
| gate | 2 | 0 | 0 | 0 | 1 | 0 | 1 |
| no_fit | 8 | 0 | 0 | 8 | 0 | 0 | 0 |
| obvious | 10 | 10 | 10 | 0 | 0 | 0 | 0 |

## By language

| Language | Cases | correct ACCEPT | NO_FIT |
|---|---|---|---|
| en | 24 | 13 | 8 |
| ja | 2 | 1 | 1 |
| mixed | 4 | 2 | 0 |
| zh | 2 | 1 | 1 |

## Economics and reliability

- Provider calls: 31; transport retries: 0
- Decision input tokens: 17936 over 31 answered cases
- Decision latency p50 / p95 ms: 998.1344999978319 / 1865.5295000062324
- Provider errors: none
- Validation violations: 0
