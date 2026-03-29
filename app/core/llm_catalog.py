LLM_OPTIONS = {
    "openai": {
        "low_cost": "gpt-5-mini",
        "best": "gpt-5",
    },
    "gemini": {
        "low_cost": "gemini-2.5-flash",
        "best": "gemini-2.5-pro",
    },
}


def resolve_model(provider: str, tier: str) -> str:
    provider_options = LLM_OPTIONS.get(provider, LLM_OPTIONS["openai"])
    return provider_options.get(tier, provider_options["low_cost"])
