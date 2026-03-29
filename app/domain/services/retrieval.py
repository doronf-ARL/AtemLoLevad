from __future__ import annotations

from sqlmodel import Session, select

from app.db.models import Playbook, Principle


class RetrievalService:
    def retrieve(self, session: Session, action: str, merged_state: dict) -> dict:
        labels = {
            *[item["label"] for item in merged_state["patient_states"]],
            *[item["label"] for item in merged_state["caregiver_states"]],
            *[item["label"] for item in merged_state["triggers"]],
        }
        playbooks = session.exec(select(Playbook).where(Playbook.status == "approved")).all()
        scored_playbooks = []
        for playbook in playbooks:
            overlap = len(labels.intersection(set(playbook.tags + playbook.applies_when)))
            action_bonus = 1 if action in playbook.tags else 0
            score = overlap * 2 + action_bonus
            scored_playbooks.append((score, playbook))
        selected_playbooks = [item[1] for item in sorted(scored_playbooks, key=lambda x: x[0], reverse=True)[:3]]

        principles = session.exec(select(Principle).where(Principle.status == "approved")).all()
        selected_principles = [
            principle for principle in principles if labels.intersection(set(principle.tags + principle.applies_to))
        ][:3]
        return {"playbooks": selected_playbooks, "principles": selected_principles}
