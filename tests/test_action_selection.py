from app.domain.services.action_selection import ActionSelectionService


def test_action_selection_falls_back_to_validate():
    service = ActionSelectionService()
    result = service.select({}, {"patient_states": [], "caregiver_states": [], "risk_snapshot": {"level": "low"}})
    assert result["action"] == "validate"
