# Decision run dec-381e63da7e12

- Provider: `clef-ollama` requesting `clef:cloud`; live: True
- Policy: `intake-placeholder` 0.1, calibrated: False, thresholds {'fit_yes': 0.7, 'fit_no': 0.3, 'route_default': 0.6}
- Question set hash: `2ee55fc0d3c86608…`
- Cases: 32; stopped early: no
- Cache: 31 hits, 0 misses; about 20,788 decision input tokens avoided
- Labels: authored for wiring, not independently reviewed. Smoke cases establish wiring, not performance.

## Outcomes

| Outcome | Count |
|---|---|
| ABSTAIN | 5 |
| ACCEPT | 16 |
| DENY | 1 |
| NO_FIT | 10 |

## Decision quality

- Top-1 route choice vs label (fits cases with an eligible labelled route, ignoring thresholds): 17/19 (89%)
- Brier score of `route_fits` vs label: 0.0251 over 31 cases
- Accepted routes matching the label: 15/16 (94%)
- Coverage (ACCEPT among labelled-fit cases): 16/20 (80%)
- No-fit recall (NO_FIT among labelled no-fit cases): 10/11 (91%)
- False accepts on no-fit cases: 0/11 (0%)
- Abstentions: 5; fallbacks: 0

## By category

| Category | Cases | ACCEPT | correct ACCEPT | NO_FIT | ABSTAIN | FALLBACK | DENY |
|---|---|---|---|---|---|---|---|
| adversarial | 2 | 0 | 0 | 2 | 0 | 0 | 0 |
| ambiguous | 10 | 6 | 5 | 0 | 4 | 0 | 0 |
| gate | 2 | 0 | 0 | 0 | 1 | 0 | 1 |
| no_fit | 8 | 0 | 0 | 8 | 0 | 0 | 0 |
| obvious | 10 | 10 | 10 | 0 | 0 | 0 | 0 |

## By language

| Language | Cases | correct ACCEPT | NO_FIT |
|---|---|---|---|
| en | 24 | 11 | 8 |
| ja | 2 | 1 | 1 |
| mixed | 4 | 2 | 0 |
| zh | 2 | 1 | 1 |

## Economics and reliability

- Provider calls: 0; transport retries: 0
- Decision input tokens: 0 over 31 answered cases
- Decision latency p50 / p95 ms: 0.21269998978823423 / 0.334200041834265
- Provider errors: none
- Validation violations: 0
