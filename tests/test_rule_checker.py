from app.domain.services.rule_check import RuleCheckService


def test_rule_checker_flags_multiple_questions():
    service = RuleCheckService()
    merged_state = {"patient_states": [], "risk_snapshot": {"level": "low"}}
    result = service.check("What happened? Are you okay?", merged_state)
    assert result["pass"] is False
    assert any(v["rule_name"] == "Max one question" for v in result["violations"])
