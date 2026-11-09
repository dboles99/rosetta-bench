# Next session plan (written 2026-11-09, end of session)

Branches: `dboles99/rosetta-bench` `exp/decision-layer` (all work, includes merged `exp/improvements`) and
`dboles99/rosetta` `exp/decision-layer` (core decision contracts and cache). Nothing is merged to `master` or `main`.
Evidence: `results/INSIGHTS.md` (findings 1-15 and follow-ups), `results/EXPERIMENT_LOG.md`, `results/COMPARISON_3x3.md`,
`notebooks/decision_layer_analysis.ipynb` (rebuild: `bench results db`, then `python notebooks/build_notebook.py .`).

## Where things stand

- Rosetta core makes no semantic calls; the decision layer is optional, default off, fail-closed, with receipts, replay
  and a canonical decision cache (exact keys only).
- Decision layer before generation: no accuracy gain on the usefulness corpora, +34-69% tokens per success (insights 2-4).
- Decision questions: clef is strong on meaning, support, notes and views (1.00) and weaker on feasibility and premise
  (0.84-0.86, Japanese worst); its distance from 0.5 is an excellent error signal (AUROC 0.99). Jev was seen on 30 items only.
- Usefulness_v2, 3 samples per arm: thinking on 0.90, reason-first 0.78, thinking off 0.63. Reason-first keeps most honest
  refusals at about half the output tokens but loses on code. Not a tie, so the Rust port was not started.
- Rejected: batching decision calls, paraphrase ensembles as a signal, similarity caching.
- Draft verdict for the brief: leaning **ADVISORY_ONLY** for the decision layer (clef questions as advisory gates with
  receipts; no route replacement). Not final until the calibration below exists.

## Owner actions (blocking)

1. Label `labelling/routing_v1_to_label.xlsx` (bench worktree), then `bench corpus import-labels` and calibrate on the
   calibration split; thresholds are frozen before any held-out run.
2. Decide whether to buy the Jev $9.90 pack for a full decision_v1 run (free tokens are used up), or stay with clef.
3. Approve publishing: merge `exp/decision-layer` to `master`, later `main` (the brief forbids it without approval).

## Planned work, in order

1. **Gate reason-first with clef `premise_valid`** on PROCEED plans (the planner let 8 of 18 false premises through);
   run on usefulness_v3, which adds the 4 REPORT_DEFECT tasks. 3 samples, compare with `bench usefulness compare`.
2. **Executor thinking for code plans only** in reason-first (code 74/99 vs 87/99 with thinking on); measure tokens per
   verified success against thinking on.
3. **Grow the corpora**: about 60 labelled items per decision question for certifiable thresholds
   (`bench decision calibrate`), and usefulness tasks towards a few hundred (5-point differences need about 500-1,000).
4. **Postflight on failing code** (follow-up 7): the hard corpus now has failures to detect.
5. **P vs M replication** (follow-up 2): the plain-prompt arm is still single-sample.
6. Final review of both branches (code review at the user's chosen level), then the written recommendation.

## Gotchas

- Use `G:\dev2\rosetta\.worktrees\.venv-exp\Scripts\python.exe`; its installed `rosetta_bench` points at the
  `exp-decision-layer` worktree, so from another worktree set `PYTHONPATH=src` (pytest does this via `pythonpath`).
- Live runs must run from a worktree whose code will not change during the run.
- The jevmodel key is read only in-process by the scratchpad helper; never print or open the credential notes file.
- clef via Ollama rejects noul `criteria` (HTTP 400); its served model name is bare `clef`.
- Any rewording of a pinned question needs a version bump, a new hash pin and a re-run against gold (insight 12).
- Offline fakes must mirror the live model on every verdict path (insight 11).
