from __future__ import annotations

from app.domain.schemas.common import ParseResult


class StateUpdateService:
    def merge_items(self, existing: list[dict], incoming: list[dict]) -> tuple[list[dict], list[dict]]:
        merged = {item["label"]: dict(item) for item in existing}
        diffs: list[dict] = []
        for new_item in incoming:
            prior = merged.get(new_item["label"])
            merged[new_item["label"]] = new_item
            diffs.append(
                {
                    "label": new_item["label"],
                    "previous": prior,
                    "new": new_item,
                    "reason": new_item.get("evidence", ""),
                }
            )
        return list(merged.values()), diffs

    def update(self, patient: dict, caregiver: dict, previous_state: dict, parse_result: ParseResult) -> dict:
        patient_states, patient_diffs = self.merge_items(
            patient.get("states", []),
            [item.model_dump() for item in parse_result.patient_state_changes],
        )
        caregiver_states, caregiver_diffs = self.merge_items(
            caregiver.get("states", []),
            [item.model_dump() for item in parse_result.caregiver_state_changes],
        )
        triggers, trigger_diffs = self.merge_items(
            patient.get("triggers", []),
            [item.model_dump() for item in parse_result.triggers],
        )
        behaviors, behavior_diffs = self.merge_items(
            patient.get("behavior_patterns", []),
            [item.model_dump() for item in parse_result.behavior_patterns],
        )
        return {
            "patient_states": patient_states,
            "caregiver_states": caregiver_states,
            "triggers": triggers,
            "behavior_patterns": behaviors,
            "interaction_pattern": parse_result.interaction_pattern or previous_state.get("interaction_pattern", ""),
            "risk_snapshot": parse_result.risk_estimate,
            "diffs": {
                "patient": patient_diffs,
                "caregiver": caregiver_diffs,
                "triggers": trigger_diffs,
                "behaviors": behavior_diffs,
            },
        }
