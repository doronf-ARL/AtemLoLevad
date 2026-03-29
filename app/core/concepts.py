CANONICAL_CONCEPTS = {
    "hyperarousal",
    "fear",
    "shame",
    "irritability",
    "withdrawal",
    "freezing",
    "dissociation_like",
    "caregiver_anxiety",
    "caregiver_over_responsibility",
    "loud_noise_trigger",
    "war_reminder_trigger",
    "pursue_withdraw_pattern",
    "grounding",
    "reduce_pressure",
    "escalation_needed",
}


def normalize_concepts(raw_values: list[str]) -> list[str]:
    normalized: list[str] = []
    for value in raw_values:
        cleaned = value.strip().lower().replace(" ", "_")
        if cleaned in CANONICAL_CONCEPTS and cleaned not in normalized:
            normalized.append(cleaned)
    return normalized
