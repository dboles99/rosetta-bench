# routing_v1

120 synthetic intake requests in 30 families of 4 variants (plain, paraphrase, Chinese or Japanese, terse or distracting).
Requests were written by Claude (2026-11-09). Gold labels come from an independent labeller via
`bench corpus sheet` / `bench corpus import-labels` into labels.jsonl. author_labels.jsonl holds the
author's own labels and is used only to measure agreement, never as gold. Do not show it to the labeller.
Splits are by family (splits.json), so paraphrases never straddle calibration and held-out.
