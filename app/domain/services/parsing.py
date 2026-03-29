from __future__ import annotations

from app.core.concepts import normalize_concepts
from app.domain.schemas.common import ParseResult, StateItem


def _contains_any(text: str, phrases: list[str]) -> bool:
    return any(phrase in text for phrase in phrases)


class ParsingService:
    def parse(self, message_text: str) -> ParseResult:
        text = message_text.lower()
        triggers: list[StateItem] = []
        patient_states: list[StateItem] = []
        caregiver_states: list[StateItem] = []
        behaviors: list[StateItem] = []
        interaction_pattern = ""
        risk = {"level": "low", "reasons": []}
        uncertainty: list[str] = []

        trigger_labels: list[str] = []
        if _contains_any(text, ["loud bang", "boom", "sirens", "explosion", "noise"]):
            trigger_labels.append("loud_noise_trigger")
        if _contains_any(text, ["war", "missile", "rocket", "reserve duty", "news"]):
            trigger_labels.append("war_reminder_trigger")
        for label in normalize_concepts(trigger_labels):
            triggers.append(StateItem(label=label, intensity="high", confidence=0.9, evidence=message_text))

        if _contains_any(text, ["froze", "frozen", "panic", "shaking", "can't breathe", "breathing fast"]):
            patient_states.append(StateItem(label="hyperarousal", intensity="high", confidence=0.88, evidence=message_text))
        if _contains_any(text, ["silent", "won't talk", "withdraw", "withdrawn", "shut down", "goes silent"]):
            patient_states.append(StateItem(label="withdrawal", intensity="high", confidence=0.82, evidence=message_text))
        if _contains_any(text, ["irritable", "snapped", "angry", "yelled"]):
            patient_states.append(StateItem(label="irritability", intensity="medium", confidence=0.76, evidence=message_text))

        if _contains_any(text, ["i keep asking", "i asked again", "what do i do", "i'm panicking", "i'm scared"]):
            caregiver_states.append(StateItem(label="caregiver_anxiety", intensity="high", confidence=0.84, evidence=message_text))
        if _contains_any(text, ["i keep asking", "asking him questions", "asking her questions", "trying to get him to talk"]):
            caregiver_states.append(StateItem(label="caregiver_over_responsibility", intensity="medium", confidence=0.78, evidence=message_text))

        if _contains_any(text, ["i keep asking", "trying to get him to talk", "he shuts down more", "goes silent"]):
            behaviors.append(StateItem(label="pursue_withdraw_pattern", intensity="medium", confidence=0.8, evidence=message_text))
            interaction_pattern = "pursue_withdraw_pattern"

        if _contains_any(text, ["suicide", "hurt himself", "hurt herself", "violent", "weapon", "ambulance"]):
            risk = {"level": "high", "reasons": ["safety concern in caregiver message"]}
        elif patient_states:
            risk = {"level": "medium", "reasons": ["acute distress indicators present"]}

        if not patient_states and not triggers:
            uncertainty.append("Parser could not confidently identify trigger or patient state.")

        return ParseResult(
            triggers=triggers,
            patient_state_changes=patient_states,
            caregiver_state_changes=caregiver_states,
            behavior_patterns=behaviors,
            interaction_pattern=interaction_pattern,
            risk_estimate=risk,
            uncertainty_notes=uncertainty,
        )
