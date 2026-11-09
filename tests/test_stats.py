import math

import pytest

from rosetta_bench.stats import cluster_means, mcnemar_exact, paired_bootstrap, paired_power


def test_cluster_means_average_repeated_samples_per_item():
    assert cluster_means({"a": [1, 0, 1], "b": [0], "c": []}) == {"a": pytest.approx(2 / 3), "b": 0.0}


def test_paired_bootstrap_is_reproducible_and_brackets_the_mean_difference():
    a = {f"t{i}": [1.0] for i in range(20)}
    b = {f"t{i}": [1.0 if i < 15 else 0.0] for i in range(20)}
    result = paired_bootstrap(a, b, n_boot=2000, seed=3)
    assert result == paired_bootstrap(a, b, n_boot=2000, seed=3)
    assert result.items == 20
    assert result.mean_diff == pytest.approx(0.25)
    assert result.ci_low <= 0.25 <= result.ci_high
    assert result.ci_low > 0  # A better on 5 of 20 items, never worse


def test_paired_bootstrap_uses_only_shared_items_and_says_when_too_few():
    result = paired_bootstrap({"x": [1.0]}, {"x": [0.0], "y": [1.0]}, n_boot=100, seed=1)
    assert result.items == 1 and result.ci_low is None and "too few" in result.note


def test_identical_arms_have_a_zero_width_interval():
    a = {f"t{i}": [float(i % 2)] for i in range(12)}
    result = paired_bootstrap(a, dict(a), n_boot=500, seed=2)
    assert result.mean_diff == 0 and result.ci_low == 0 and result.ci_high == 0


def test_mcnemar_exact_matches_the_binomial_tail():
    assert mcnemar_exact(0, 0) == 1.0
    assert mcnemar_exact(5, 0) == pytest.approx(2 * 0.5 ** 5)  # 0.0625
    assert mcnemar_exact(3, 3) == 1.0


def test_paired_power_reports_items_needed_and_the_ratio():
    # 10% discordant pairs, detect 5 points at alpha 0.05 and 80% power
    needed = paired_power(discordance=0.10, delta=0.05, alpha=0.05, power=0.80)
    assert needed == math.ceil((1.959964 + 0.841621) ** 2 * 0.10 / 0.05 ** 2)
    assert paired_power(discordance=0.0, delta=0.05) == 0
