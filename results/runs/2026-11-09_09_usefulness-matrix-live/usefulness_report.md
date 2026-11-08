# Usefulness matrix use-ed79aa225cee

- Generator: `ollama` `kimi-k2.7-code:cloud` settings {'temperature': 0, 'seed': 20261109}; live: True
- Representations: **P** = plain prose prompt (the contract's hand-written notes, no Rosetta structure); **H** = Rosetta human view (.md: generated field list plus notes); **M** = Rosetta machine view (.cpn packet, loaded by rosetta_core.loader)
- Deciders: none, jevmodel, clef-ollama, consensus; providers: `jevmodel` → `jev-latest` (calibrated: False), `clef-ollama` → `clef:cloud` (calibrated: False)
- Trials: 216; stopped early: no
- Accounting: Identical prompts share one generation and identical code one sandbox run; each arm is charged the original call's tokens and time. Decisions are made once per provider and task.

## Matrix

Each cell: verified successes / trials · tokens per verified success · p50 attributed ms.

| Representation | none | jevmodel | clef-ollama | consensus |
|---|---|---|---|---|
| P | 18/18 · 1,235 · 4,878 | 18/18 · 2,062 · 6,259 | 18/18 · 1,884 · 6,086 | 18/18 · 2,769 · 7,466 |
| H | 18/18 · 781 · 4,495 | 18/18 · 1,523 · 5,265 | 18/18 · 1,345 · 4,901 | 18/18 · 2,230 · 6,256 |
| M | 18/18 · 684 · 4,536 | 18/18 · 2,003 · 7,200 | 18/18 · 1,693 · 6,071 | 18/18 · 2,187 · 6,498 |

## Per arm

| Arm | Trials | Accuracy | Code passed | No-code handled | Decline precision | Decline recall | Code tasks on code route | Generator calls charged | Generator tokens | Decision tokens | Tokens per verified success | p50 / p95 ms | Errors | Timeouts |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P+none | 18 | 100% | 12/12 | 6/6 | – | 0% | 100% | 18 | 22,232 | 0 | 1,235 | 4,878 / 46,132 | 0 | 0 |
| P+jevmodel | 18 | 100% | 12/12 | 6/6 | 100% | 100% | 100% | 12 | 21,190 | 15,928 | 2,062 | 6,259 / 47,834 | 0 | 0 |
| P+clef-ollama | 18 | 100% | 12/12 | 6/6 | 100% | 100% | 100% | 12 | 21,190 | 12,725 | 1,884 | 6,086 / 46,691 | 0 | 0 |
| P+consensus | 18 | 100% | 12/12 | 6/6 | 100% | 100% | 100% | 12 | 21,190 | 28,653 | 2,769 | 7,466 / 48,393 | 0 | 0 |
| H+none | 18 | 100% | 12/12 | 6/6 | – | 0% | 100% | 18 | 14,063 | 0 | 781 | 4,495 / 21,666 | 0 | 0 |
| H+jevmodel | 18 | 100% | 12/12 | 6/6 | 100% | 100% | 100% | 12 | 11,482 | 15,928 | 1,523 | 5,265 / 23,087 | 0 | 0 |
| H+clef-ollama | 18 | 100% | 12/12 | 6/6 | 100% | 100% | 100% | 12 | 11,482 | 12,725 | 1,345 | 4,901 / 22,942 | 0 | 0 |
| H+consensus | 18 | 100% | 12/12 | 6/6 | 100% | 100% | 100% | 12 | 11,482 | 28,653 | 2,230 | 6,256 / 24,363 | 0 | 0 |
| M+none | 18 | 100% | 12/12 | 6/6 | – | 0% | 100% | 18 | 12,304 | 0 | 684 | 4,536 / 28,122 | 0 | 0 |
| M+jevmodel | 18 | 100% | 12/12 | 6/6 | 100% | 100% | 100% | 12 | 10,705 | 25,343 | 2,003 | 7,200 / 31,235 | 0 | 0 |
| M+clef-ollama | 18 | 100% | 12/12 | 6/6 | 100% | 100% | 100% | 12 | 10,705 | 19,768 | 1,693 | 6,071 / 29,536 | 0 | 0 |
| M+consensus | 18 | 100% | 12/12 | 6/6 | 100% | 100% | 100% | 12 | 10,705 | 28,653 | 2,187 | 6,498 / 30,384 | 0 | 0 |

## Representation contrasts

Plain prompt (P) against Rosetta (H, M), within each decision mode.

| Contrast (A vs B) | Paired tasks | A better | B better | Accuracy A−B | Tokens/success A vs B | p50 A vs B |
|---|---|---|---|---|---|---|
| P vs H · none | 18 | 0 | 0 | 0.0 pp | 58% | 9% |
| P vs M · none | 18 | 0 | 0 | 0.0 pp | 81% | 8% |
| H vs M · none | 18 | 0 | 0 | 0.0 pp | 14% | -1% |
| P vs H · jevmodel | 18 | 0 | 0 | 0.0 pp | 35% | 19% |
| P vs M · jevmodel | 18 | 0 | 0 | 0.0 pp | 3% | -13% |
| H vs M · jevmodel | 18 | 0 | 0 | 0.0 pp | -24% | -27% |
| P vs H · clef-ollama | 18 | 0 | 0 | 0.0 pp | 40% | 24% |
| P vs M · clef-ollama | 18 | 0 | 0 | 0.0 pp | 11% | 0% |
| H vs M · clef-ollama | 18 | 0 | 0 | 0.0 pp | -21% | -19% |
| P vs H · consensus | 18 | 0 | 0 | 0.0 pp | 24% | 19% |
| P vs M · consensus | 18 | 0 | 0 | 0.0 pp | 27% | 15% |
| H vs M · consensus | 18 | 0 | 0 | 0.0 pp | 2% | -4% |

## Decision contrasts

Without and with each decision layer, within each representation.

| Contrast (A vs B) | Paired tasks | A better | B better | Accuracy A−B | Tokens/success A vs B | p50 A vs B |
|---|---|---|---|---|---|---|
| none vs jevmodel · P | 18 | 0 | 0 | 0.0 pp | -40% | -22% |
| none vs clef-ollama · P | 18 | 0 | 0 | 0.0 pp | -34% | -20% |
| none vs consensus · P | 18 | 0 | 0 | 0.0 pp | -55% | -35% |
| jevmodel vs clef-ollama · P | 18 | 0 | 0 | 0.0 pp | 9% | 3% |
| jevmodel vs consensus · P | 18 | 0 | 0 | 0.0 pp | -26% | -16% |
| clef-ollama vs consensus · P | 18 | 0 | 0 | 0.0 pp | -32% | -18% |
| none vs jevmodel · H | 18 | 0 | 0 | 0.0 pp | -49% | -15% |
| none vs clef-ollama · H | 18 | 0 | 0 | 0.0 pp | -42% | -8% |
| none vs consensus · H | 18 | 0 | 0 | 0.0 pp | -65% | -28% |
| jevmodel vs clef-ollama · H | 18 | 0 | 0 | 0.0 pp | 13% | 7% |
| jevmodel vs consensus · H | 18 | 0 | 0 | 0.0 pp | -32% | -16% |
| clef-ollama vs consensus · H | 18 | 0 | 0 | 0.0 pp | -40% | -22% |
| none vs jevmodel · M | 18 | 0 | 0 | 0.0 pp | -66% | -37% |
| none vs clef-ollama · M | 18 | 0 | 0 | 0.0 pp | -60% | -25% |
| none vs consensus · M | 18 | 0 | 0 | 0.0 pp | -69% | -30% |
| jevmodel vs clef-ollama · M | 18 | 0 | 0 | 0.0 pp | 18% | 19% |
| jevmodel vs consensus · M | 18 | 0 | 0 | 0.0 pp | -8% | 11% |
| clef-ollama vs consensus · M | 18 | 0 | 0 | 0.0 pp | -23% | -7% |

## Decision providers on these tasks

| Provider | Tasks | ACCEPT | NO_FIT | ABSTAIN | FALLBACK | Code→code_change | No-code→NO_FIT | Tokens | p50 ms |
|---|---|---|---|---|---|---|---|---|---|
| clef-ollama | 18 | 12 | 6 | 0 | 0 | 12/12 | 6/6 | 12,725 | 598 |
| jevmodel | 18 | 12 | 6 | 0 | 0 | 12/12 | 6/6 | 15,928 | 1,428 |

## Postflight (advisory)

| Provider | Code checked | Mean p on passing code | Mean p on failing code | Failing flagged (p<0.5) | Passing flagged |
|---|---|---|---|---|---|
| clef-ollama | 12 | 0.899 | – | 0/0 | 1/12 |
| jevmodel | 12 | 0.904 | – | 0/0 | 0/12 |
