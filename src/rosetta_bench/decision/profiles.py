"""Provider profiles. Limits come from each provider's own documentation, with the
date read; anything not documented is None ("unknown") and must be probed, not assumed."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderProfile:
    name: str
    endpoint: str
    api_key_env: str | None
    default_model: str
    pricing_tool: str
    max_questions_per_call: int
    max_choice_options: int
    score_base: float | None  # number the provider gives the lowest level when no legend is returned
    pins_versions: bool
    supports_idempotency_key: bool
    notes: str


PROFILES: dict[str, ProviderProfile] = {
    "jevmodel": ProviderProfile(
        name="jevmodel",
        endpoint="https://jevmodel.org/v1/systemone",
        api_key_env="JEVMODEL_API_KEY",
        default_model="jev-latest",
        pricing_tool="JEVMODEL",
        max_questions_per_call=8,
        max_choice_options=20,
        score_base=None,
        pins_versions=False,
        supports_idempotency_key=True,
        notes=(
            "jevmodel.org/docs read 2026-11-09: unaffiliated reseller of TypeSafe's Jev; 1-8 questions, "
            "choice 2-20 options, score returns score+confidence only, only jev-latest/jev-preview, "
            "120 requests/min per key, no Retry-After documented."
        ),
    ),
    "clef-ollama": ProviderProfile(
        name="clef-ollama",
        endpoint="http://localhost:11434/v1/systemone",
        api_key_env=None,
        default_model="clef:cloud",
        pricing_tool="OLLAMA",
        max_questions_per_call=64,
        max_choice_options=26,
        score_base=None,
        pins_versions=False,
        supports_idempotency_key=False,
        notes=(
            "Local Ollama forwarding to Ollama Cloud (verified working 2026-11-05 per local skill notes); "
            "clef docs: up to 64 questions; choice 2-26 options locally. Served revision not pinnable here."
        ),
    ),
    "fake": ProviderProfile(
        name="fake",
        endpoint="fake://systemone",
        api_key_env=None,
        default_model="fake-systemone-1",
        pricing_tool="FAKE",
        max_questions_per_call=64,
        max_choice_options=26,
        score_base=None,
        pins_versions=True,
        supports_idempotency_key=False,
        notes="Offline synthetic keyword-overlap provider. Not a model.",
    ),
}
