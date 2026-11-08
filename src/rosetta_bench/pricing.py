# USD per 1,000 tokens: (input_price, output_price). Static snapshot, not live-fetched;
# update when tool pricing changes. Unlisted (tool, model) pairs cost 0.0.
#
# LEGACY: these figures are unverified placeholders kept so old results and tests read
# the same. New results use `estimate_cost_v2`, which never treats an unknown price as 0.
from dataclasses import dataclass

PRICING_PER_1K_TOKENS: dict[tuple[str, str], tuple[float, float]] = {
    ("CLAUDE", "claude-sonnet-5"): (0.003, 0.015),
    ("AZURE_OPENAI", "gpt-4o"): (0.005, 0.015),
    ("OLLAMA", "llama3"): (0.0, 0.0),
}


def estimate_cost(tool: str, model: str, tokens_in: int, tokens_out: int) -> float:
    price_in, price_out = PRICING_PER_1K_TOKENS.get((tool, model), (0.0, 0.0))
    return (tokens_in / 1000) * price_in + (tokens_out / 1000) * price_out


@dataclass(frozen=True)
class PriceEntry:
    input_per_mtok: float
    output_per_mtok: float
    source: str
    as_of: str


@dataclass(frozen=True)
class CostEstimate:
    usd: float | None
    basis: str  # priced | unknown | free_local | subscription | legacy_unverified
    price_source: str | None
    price_as_of: str | None

    def to_dict(self) -> dict:
        return {"usd": self.usd, "basis": self.basis, "price_source": self.price_source, "price_as_of": self.price_as_of}


# Only prices read from a primary source, with the date they were read.
VERIFIED_PRICES: dict[tuple[str, str], PriceEntry] = {
    ("JEVMODEL", "jev-latest"): PriceEntry(
        0.66, 0.0, "jevmodel.org/pricing: one-time pack $9.90 for 15M input tokens; output free", "2026-11-09"
    ),
    ("TYPESAFE", "jev-1.14.0"): PriceEntry(0.042, 0.0, "docs.typesafe.ai/models: $42 per billion input tokens", "2026-11-09"),
    ("TYPESAFE", "jev-1.13.0"): PriceEntry(0.042, 0.0, "docs.typesafe.ai/models: $42 per billion input tokens", "2026-11-09"),
}

_FREE_TOOLS = {"FAKE", "STUB"}


def _is_ollama_cloud(model: str) -> bool:
    return ":cloud" in model or model.endswith("-cloud")


def lookup_price(tool: str, model: str) -> PriceEntry | None:
    return VERIFIED_PRICES.get((tool, model))


def estimate_cost_v2(tool: str, model: str, tokens_in: int | None, tokens_out: int | None) -> CostEstimate:
    if tool in _FREE_TOOLS:
        return CostEstimate(0.0, "free_local", "offline stand-in, no model call", None)
    if tool == "OLLAMA":
        if _is_ollama_cloud(model):
            return CostEstimate(None, "subscription", "Ollama Cloud subscription; per-call price not published", None)
        return CostEstimate(0.0, "free_local", "local Ollama model", None)
    entry = lookup_price(tool, model)
    if entry is None or tokens_in is None or tokens_out is None:
        return CostEstimate(None, "unknown", None, None)
    usd = (tokens_in / 1_000_000) * entry.input_per_mtok + (tokens_out / 1_000_000) * entry.output_per_mtok
    return CostEstimate(usd, "priced", entry.source, entry.as_of)
