from __future__ import annotations

from app.core.rules import RuleViolation, count_question_marks, has_confrontational_language, has_diagnosis_claim, is_concise


class RuleCheckService:
    def check(self, text: str, merged_state: dict) -> dict:
        violations: list[RuleViolation] = []
        if count_question_marks(text) > 1:
            violations.append(
                RuleViolation(
                    rule_name="Max one question",
                    description="Response contains more than one question.",
                    severity="medium",
                    suggestion="Keep at most one micro-question.",
                )
            )
        if has_diagnosis_claim(text):
            violations.append(
                RuleViolation(
                    rule_name="No diagnosis as fact",
                    description="Response states a diagnosis as certain.",
                    severity="high",
                    suggestion="Describe observed distress without diagnosing.",
                )
            )
        high_arousal = any(item["label"] == "hyperarousal" for item in merged_state["patient_states"])
        if high_arousal and has_confrontational_language(text):
            violations.append(
                RuleViolation(
                    rule_name="No confrontation in high arousal",
                    description="Response uses pushing or confrontation language in acute distress.",
                    severity="high",
                    suggestion="Replace with calm, low-pressure guidance.",
                )
            )
        if merged_state["risk_snapshot"].get("level") == "high" and "outside help" not in text.lower():
            violations.append(
                RuleViolation(
                    rule_name="Escalation required",
                    description="High-risk case must include escalation wording.",
                    severity="high",
                    suggestion="Mention contacting clinician or emergency support.",
                )
            )
        if not is_concise(text):
            violations.append(
                RuleViolation(
                    rule_name="Keep response concise",
                    description="Response is too long for the MVP constraint.",
                    severity="low",
                    suggestion="Trim to one short paragraph and one immediate step.",
                )
            )
        return {
            "pass": not violations,
            "violations": [violation.__dict__ for violation in violations],
        }

    def revise(self, text: str, rule_result: dict) -> str:
        revised = text
        if any(v["rule_name"] == "Max one question" for v in rule_result["violations"]):
            first_part, _, _ = revised.partition("?")
            revised = first_part + "?"
        if any(v["rule_name"] == "No diagnosis as fact" for v in rule_result["violations"]):
            revised = revised.replace("This is definitely PTSD.", "This may be trauma-related distress.")
        if any(v["rule_name"] == "Keep response concise" for v in rule_result["violations"]):
            words = revised.split()
            revised = " ".join(words[:90])
        return revised
