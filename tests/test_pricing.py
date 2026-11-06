from rosetta_bench.pricing import estimate_cost


def test_known_tool_and_model_computes_cost():
    cost = estimate_cost("CLAUDE", "claude-sonnet-5", tokens_in=1000, tokens_out=1000)
    assert cost > 0


def test_unknown_tool_or_model_returns_zero():
    assert estimate_cost("UNKNOWN_TOOL", "unknown-model", tokens_in=1000, tokens_out=1000) == 0.0


def test_zero_tokens_costs_zero():
    assert estimate_cost("CLAUDE", "claude-sonnet-5", tokens_in=0, tokens_out=0) == 0.0


def test_ollama_local_model_is_free():
    assert estimate_cost("OLLAMA", "llama3", tokens_in=100000, tokens_out=100000) == 0.0
