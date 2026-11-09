# Paraphrase ensemble: run `eval-fb40c3024b8b` (clef-ollama)

Each yes/no question asked in 3 wordings in one call. *Single* = the pinned wording alone; *ensemble* = mean of the 3 probabilities; *majority* = 2 of 3 verdicts. Verdicts use the placeholder 0.7 / 0.3 band. An abstention counts against accuracy. AUROC: how well a signal ranks the single wording's errors (wrong or abstained) above its correct answers; 0.5 = no better than chance. *Spread* = max - min of the 3 probabilities; *margin doubt* = 1 - |2p - 1| of the single answer.

| Question | Items | Single acc. | Ensemble acc. | Majority acc. | Single risk | Ensemble risk | Mean spread | Verdicts differ | AUROC spread | AUROC margin doubt | AUROC both |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **all** | 154 | 0.93 | 0.89 | 0.93 | 0.021 | 0.021 | 0.17 | 0.26 | 0.68 | 0.99 | 0.93 |
| meaning_changed | 20 | 1.00 | 1.00 | 1.00 | 0.000 | 0.000 | 0.04 | 0.00 | n/a | n/a | n/a |
| notes_consistent | 20 | 1.00 | 1.00 | 1.00 | 0.000 | 0.000 | 0.05 | 0.05 | n/a | n/a | n/a |
| output_supported | 20 | 1.00 | 1.00 | 1.00 | 0.000 | 0.000 | 0.01 | 0.00 | n/a | n/a | n/a |
| premise_valid | 32 | 0.84 | 0.84 | 0.84 | 0.069 | 0.069 | 0.06 | 0.09 | 0.94 | 0.97 | 0.97 |
| requirements_sufficient | 20 | 0.95 | 0.70 | 0.95 | 0.000 | 0.000 | 0.41 | 0.75 | 0.42 | 1.00 | 1.00 |
| task_feasible | 22 | 0.77 | 0.77 | 0.77 | 0.056 | 0.056 | 0.06 | 0.05 | 0.82 | 0.99 | 0.99 |
| views_equivalent | 20 | 1.00 | 0.95 | 1.00 | 0.000 | 0.000 | 0.63 | 1.00 | n/a | n/a | n/a |

Spread >= 0.3 flags 1 of 11 single-wording errors.

## Fragile answers (spread >= 0.3): 31

| Question | Item | Gold | p (3 wordings) |
|---|---|---|---|
| requirements_sufficient | req-en-01-complete | True | 0.94, 0.92, 0.22 |
| requirements_sufficient | req-en-02-complete | True | 0.90, 0.88, 0.23 |
| requirements_sufficient | req-en-03-complete | True | 0.91, 0.90, 0.19 |
| requirements_sufficient | req-en-04-complete | True | 0.82, 0.82, 0.38 |
| requirements_sufficient | req-ja-08-complete | True | 0.96, 0.94, 0.45 |
| requirements_sufficient | req-ja-09-complete | True | 0.40, 0.63, 0.31 |
| requirements_sufficient | req-ja-10-complete | True | 0.95, 0.94, 0.28 |
| requirements_sufficient | req-ja-10-missing | False | 0.05, 0.05, 0.39 |
| requirements_sufficient | req-zh-05-complete | True | 0.93, 0.90, 0.37 |
| requirements_sufficient | req-zh-06-complete | True | 0.83, 0.79, 0.21 |
| requirements_sufficient | req-zh-07-complete | True | 0.93, 0.92, 0.38 |
| requirements_sufficient | req-zh-07-missing | False | 0.10, 0.09, 0.42 |
| views_equivalent | views-en-01-changed-cpn | False | 0.02, 0.03, 0.84 |
| views_equivalent | views-en-01-equal-reorder | True | 0.97, 0.96, 0.28 |
| views_equivalent | views-en-02-changed-md | False | 0.01, 0.03, 0.64 |
| views_equivalent | views-en-02-equal-md | True | 0.96, 0.95, 0.32 |
| views_equivalent | views-en-03-changed-cpn | False | 0.02, 0.04, 0.58 |
| views_equivalent | views-en-03-equal-md | True | 0.95, 0.93, 0.24 |
| views_equivalent | views-en-04-changed-md | False | 0.03, 0.08, 0.63 |
| views_equivalent | views-en-04-equal-reorder | True | 0.95, 0.95, 0.35 |
| views_equivalent | views-en-05-changed-cpn | False | 0.02, 0.03, 0.74 |
| views_equivalent | views-en-05-equal-reorder | True | 0.96, 0.96, 0.38 |
| views_equivalent | views-ja-01-equal-reorder | True | 0.96, 0.96, 0.22 |
| views_equivalent | views-ja-02-changed-cpn | False | 0.02, 0.03, 0.40 |
| views_equivalent | views-ja-02-equal-md | True | 0.95, 0.95, 0.39 |
| views_equivalent | views-zh-01-changed-cpn | False | 0.02, 0.03, 0.75 |
| views_equivalent | views-zh-01-equal-md | True | 0.96, 0.95, 0.52 |
| views_equivalent | views-zh-02-changed-md | False | 0.02, 0.04, 0.81 |
| views_equivalent | views-zh-02-equal-reorder | True | 0.96, 0.96, 0.17 |
| views_equivalent | views-zh-03-changed-cpn | False | 0.01, 0.02, 0.80 |
| views_equivalent | views-zh-03-equal-md | True | 0.94, 0.94, 0.33 |
