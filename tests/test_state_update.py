from app.domain.schemas.common import ParseResult, StateItem
from app.domain.services.state_update import StateUpdateService


def test_state_merge_replaces_same_label_and_logs_diff():
    service = StateUpdateService()
    parse_result = ParseResult(patient_state_changes=[StateItem(label="hyperarousal", intensity="high", confidence=0.9, evidence="new event")])
    merged = service.update(
        patient={"states": [{"label": "hyperarousal", "intensity": "medium", "confidence": 0.5, "evidence": "old"}], "triggers": [], "behavior_patterns": []},
        caregiver={"states": []},
        previous_state={},
        parse_result=parse_result,
    )
    assert merged["patient_states"][0]["intensity"] == "high"
    assert merged["diffs"]["patient"][0]["previous"]["intensity"] == "medium"
