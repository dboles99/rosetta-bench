# Decision run dec-f2665c016492

- Provider: `clef-ollama` requesting `clef:cloud`; live: True
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

- Top-1 route choice vs label (fits cases with an eligible labelled route, ignoring thresholds): 18/19 (95%)
- Brier score of `route_fits` vs label: 0.0246 over 31 cases
- Accepted routes matching the label: 16/17 (94%)
- Coverage (ACCEPT among labelled-fit cases): 17/20 (85%)
- No-fit recall (NO_FIT among labelled no-fit cases): 10/11 (91%)
- False accepts on no-fit cases: 0/11 (0%)
- Abstentions: 4; fallbacks: 0

## By category

| Category | Cases | ACCEPT | correct ACCEPT | NO_FIT | ABSTAIN | FALLBACK | DENY |
|---|---|---|---|---|---|---|---|
| adversarial | 2 | 0 | 0 | 2 | 0 | 0 | 0 |
| ambiguous | 10 | 7 | 6 | 0 | 3 | 0 | 0 |
| gate | 2 | 0 | 0 | 0 | 1 | 0 | 1 |
| no_fit | 8 | 0 | 0 | 8 | 0 | 0 | 0 |
| obvious | 10 | 10 | 10 | 0 | 0 | 0 | 0 |

## By language

| Language | Cases | correct ACCEPT | NO_FIT |
|---|---|---|---|
| en | 24 | 11 | 8 |
| ja | 2 | 1 | 1 |
| mixed | 4 | 3 | 0 |
| zh | 2 | 1 | 1 |

## Economics and reliability

- Provider calls: 31; transport retries: 0
- Decision input tokens: 20788 over 31 answered cases
- Decision latency p50 / p95 ms: 874.873899971135 / 1395.3899000189267
- Provider errors: none
- Validation violations: 0
