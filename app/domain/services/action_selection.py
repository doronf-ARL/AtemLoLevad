from __future__ import annotations


class ActionSelectionService:
    def select(self, parse_result: dict, merged_state: dict) -> dict:
        risk_level = merged_state["risk_snapshot"].get("level", "low")
        patient_labels = {item["label"] for item in merged_state["patient_states"]}
        caregiver_labels = {item["label"] for item in merged_state["caregiver_states"]}

        if risk_level == "high":
            return {"action": "escalate", "micro_question": None, "reason": "high risk condition"}
        if "hyperarousal" in patient_labels:
            return {
                "action": "ground",
                "micro_question": "Can you stay nearby and speak in one calm sentence?",
                "reason": "acute high arousal detected",
            }
        if "withdrawal" in patient_labels and "caregiver_anxiety" in caregiver_labels:
            return {"action": "reduce_pressure", "micro_question": None, "reason": "reduce pursuit pressure"}
        if "pursue_withdraw_pattern" == merged_state.get("interaction_pattern"):
            return {"action": "reduce_pressure", "micro_question": None, "reason": "interaction loop present"}
        if "irritability" in patient_labels:
            return {"action": "set_boundary", "micro_question": None, "reason": "boundary-setting scenario"}
        return {"action": "validate", "micro_question": None, "reason": "fallback supportive action"}
