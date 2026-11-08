import pytest

from rosetta_bench.pricing import CostEstimate, estimate_cost, estimate_cost_v2, lookup_price


def test_unknown_model_cost_is_unknown_not_zero():
    estimate = estimate_cost_v2("CLAUDE", "some-unlisted-model", 1000, 1000)
    assert estimate.usd is None
    assert estimate.basis == "unknown"


def test_legacy_estimate_is_unchanged_for_unknown_models():
    assert estimate_cost("UNKNOWN_TOOL", "unknown-model", tokens_in=1000, tokens_out=1000) == 0.0


def test_placeholder_legacy_prices_are_not_trusted_by_v2():
    estimate = estimate_cost_v2("CLAUDE", "claude-sonnet-5", 1000, 1000)
    assert estimate.basis == "unknown"
    assert estimate.usd is None


def test_ollama_cloud_models_are_subscription_priced():
    for model in ("kimi-k2.7-code:cloud", "clef:27b-cloud", "clef:cloud"):
        estimate = estimate_cost_v2("OLLAMA", model, 1000, 500)
        assert (estimate.usd, estimate.basis) == (None, "subscription"), model


def test_local_ollama_models_are_free():
    estimate = estimate_cost_v2("OLLAMA", "llama3", 1000, 500)
    assert (estimate.usd, estimate.basis) == (0.0, "free_local")


def test_fake_generators_cost_nothing_and_say_why():
    estimate = estimate_cost_v2("FAKE", "echo-1", 1000, 500)
    assert (estimate.usd, estimate.basis) == (0.0, "free_local")


def test_priced_entries_carry_source_and_date():
    entry = lookup_price("JEVMODEL", "jev-latest")
    assert entry is not None
    assert entry.source
    assert entry.as_of == "2026-11-09"
    estimate = estimate_cost_v2("JEVMODEL", "jev-latest", 1_000_000, 50)
    assert estimate.basis == "priced"
    assert estimate.usd == pytest.approx(0.66)
    assert estimate.price_as_of == "2026-11-09"


def test_lookup_of_an_unlisted_model_returns_none():
    assert lookup_price("CLAUDE", "some-unlisted-model") is None


def test_cost_estimate_serialises_for_receipts():
    estimate = CostEstimate(usd=None, basis="unknown", price_source=None, price_as_of=None)
    assert estimate.to_dict() == {"usd": None, "basis": "unknown", "price_source": None, "price_as_of": None}
