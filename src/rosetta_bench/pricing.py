# USD per 1,000 tokens: (input_price, output_price). Static snapshot, not live-fetched;
# update when tool pricing changes. Unlisted (tool, model) pairs cost 0.0.
PRICING_PER_1K_TOKENS: dict[tuple[str, str], tuple[float, float]] = {
    ("CLAUDE", "claude-sonnet-5"): (0.003, 0.015),
    ("AZURE_OPENAI", "gpt-4o"): (0.005, 0.015),
    ("OLLAMA", "llama3"): (0.0, 0.0),
}


def estimate_cost(tool: str, model: str, tokens_in: int, tokens_out: int) -> float:
    price_in, price_out = PRICING_PER_1K_TOKENS.get((tool, model), (0.0, 0.0))
    return (tokens_in / 1000) * price_in + (tokens_out / 1000) * price_out
