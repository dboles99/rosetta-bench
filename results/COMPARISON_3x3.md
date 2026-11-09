# Arm comparison (paired by task)

Samples are averaged per task before comparing; intervals are percentile bootstraps over tasks. McNemar uses each task's majority outcome (success in more than half of its samples), so a task split evenly across an even number of samples counts as a failure there but still moves the bootstrap.

| Arm | Samples | Tasks | Accuracy | Tokens per verified success | Mean reasoning tokens (est.) | p50 / p95 ms |
|---|---|---|---|---|---|---|
| think_on | 3 | 66 | 0.899 | 4,041 | 2,971 | 6,956 / 145,621 |
| reason_first | 3 | 66 | 0.778 | 3,584 | 1,176 | 8,012 / 41,591 |
| think_off | 3 | 66 | 0.626 | 1,179 | 0 | 2,255 / 8,295 |

| Contrast | Tasks | A better | B better | Accuracy A−B (95% CI) | Tokens per task A−B (95% CI) | McNemar p | items needed for 5 pp | have / need |
|---|---|---|---|---|---|---|---|---|
| think_on vs reason_first | 66 | 21 | 4 | 0.121 (0.051, 0.192) | 845 (209, 1,578) | 0.109 | 476 | 0.14 |
| think_on vs think_off | 66 | 27 | 3 | 0.273 (0.172, 0.374) | 2,894 (1,894, 4,094) | 0.000 | 1047 | 0.06 |
| reason_first vs think_off | 66 | 19 | 5 | 0.152 (0.066, 0.242) | 2,050 (1,578, 2,688) | 0.004 | 762 | 0.09 |
