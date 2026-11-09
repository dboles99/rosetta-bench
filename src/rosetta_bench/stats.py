"""Paired, item-clustered statistics for small LLM evaluations.

Items (tasks) are the unit of resampling: repeated samples of the same item are averaged first,
then the paired difference is bootstrapped over items (Miller 2024, arXiv:2411.00640). Power is
reported as the number of items needed for a given difference (Card et al. 2020; Kotawala 2026).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from statistics import NormalDist


@dataclass(frozen=True)
class PairedResult:
    items: int
    mean_diff: float | None
    ci_low: float | None
    ci_high: float | None
    note: str = ""


def cluster_means(values: dict[str, list]) -> dict[str, float]:
    return {item: sum(samples) / len(samples) for item, samples in values.items() if samples}


def paired_bootstrap(a: dict[str, list], b: dict[str, list], *, n_boot: int = 10_000, seed: int = 0,
                     level: float = 0.95) -> PairedResult:
    """Mean of (A - B) over shared items, with a percentile bootstrap interval resampling items."""
    mean_a, mean_b = cluster_means(a), cluster_means(b)
    shared = sorted(set(mean_a) & set(mean_b))
    if not shared:
        return PairedResult(0, None, None, None, "no shared items")
    diffs = [mean_a[item] - mean_b[item] for item in shared]
    mean = sum(diffs) / len(diffs)
    if len(shared) < 2:
        return PairedResult(len(shared), mean, None, None, "too few paired items for an interval")
    rng = random.Random(seed)
    n = len(diffs)
    boots = sorted(sum(rng.choices(diffs, k=n)) / n for _ in range(n_boot))
    low = boots[int((1 - level) / 2 * n_boot)]
    high = boots[min(n_boot - 1, int((1 + level) / 2 * n_boot) - 1)]
    return PairedResult(len(shared), mean, low, high)


def mcnemar_exact(a_only: int, b_only: int) -> float:
    """Two-sided exact McNemar p-value from the discordant counts."""
    n = a_only + b_only
    if n == 0:
        return 1.0
    k = min(a_only, b_only)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def paired_power(discordance: float, delta: float, alpha: float = 0.05, power: float = 0.80) -> int:
    """Items needed to detect a paired accuracy difference `delta` when a fraction `discordance`
    of items disagree between arms (normal approximation)."""
    if discordance <= 0:
        return 0
    z = NormalDist().inv_cdf(1 - alpha / 2) + NormalDist().inv_cdf(power)
    return math.ceil(z ** 2 * discordance / delta ** 2)
