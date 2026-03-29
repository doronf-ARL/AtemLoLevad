from __future__ import annotations

from sqlmodel import Session, select

from app.core.config import settings
from app.db.models import AuditLog, DraftResponse, InteractionState, Message, PersonModel, Thread
from app.domain.services.action_selection import ActionSelectionService
from app.domain.services.generation import GenerationService
from app.domain.services.parsing import ParsingService
from app.domain.services.retrieval import RetrievalService
from app.domain.services.rule_check import RuleCheckService
from app.domain.services.state_update import StateUpdateService


class PipelineService:
    def __init__(self) -> None:
        self.parser = ParsingService()
        self.state_updater = StateUpdateService()
        self.action_selector = ActionSelectionService()
        self.retriever = RetrievalService()
        self.generator = GenerationService()
        self.rule_checker = RuleCheckService()

    def process_message(self, session: Session, thread: Thread, message: Message) -> DraftResponse:
        patient = session.get(PersonModel, thread.patient_id)
        caregiver = session.get(PersonModel, thread.caregiver_id)
        if not patient or not caregiver:
            raise ValueError("Thread must reference an existing patient and caregiver.")
        previous_state = session.exec(select(InteractionState).where(InteractionState.thread_id == thread.id).order_by(InteractionState.id.desc())).first()

        parse_result = self.parser.parse(message.content)
        merged = self.state_updater.update(
            patient=patient.model_dump(),
            caregiver=caregiver.model_dump(),
            previous_state=previous_state.model_dump() if previous_state else {},
            parse_result=parse_result,
        )
        patient.states = merged["patient_states"]
        patient.triggers = merged["triggers"]
        patient.behavior_patterns = merged["behavior_patterns"]
        caregiver.states = merged["caregiver_states"]
        patient.risk = merged["risk_snapshot"]
        caregiver.risk = merged["risk_snapshot"]
        session.add(patient)
        session.add(caregiver)

        interaction = InteractionState(
            thread_id=thread.id,
            patient_id=patient.id,
            caregiver_id=caregiver.id,
            current_trigger=merged["triggers"][0]["label"] if merged["triggers"] else "",
            patient_state_snapshot={"items": merged["patient_states"]},
            caregiver_state_snapshot={"items": merged["caregiver_states"]},
            interaction_pattern=merged["interaction_pattern"],
            risk_snapshot=merged["risk_snapshot"],
            decision_need="support_next_step",
            raw_message_excerpt=message.content[:250],
            structured_observations=parse_result.model_dump(),
        )
        session.add(interaction)
        session.commit()
        session.refresh(interaction)

        selection = self.action_selector.select(parse_result.model_dump(), merged)
        knowledge = self.retriever.retrieve(session, selection["action"], merged)
        draft_text = self.generator.generate(
            caregiver_message=message.content,
            action=selection["action"],
            merged_state=merged,
            knowledge=knowledge,
            micro_question=selection["micro_question"],
        )
        rule_result = self.rule_checker.check(draft_text, merged)
        revised_text = draft_text if rule_result["pass"] else self.rule_checker.revise(draft_text, rule_result)
        second_rule_result = self.rule_checker.check(revised_text, merged)

        draft = DraftResponse(
            message_id=message.id,
            interaction_state_id=interaction.id,
            selected_action=selection["action"],
            selected_playbooks=[playbook.id for playbook in knowledge["playbooks"]],
            draft_text=draft_text,
            rule_check_results={
                "initial": rule_result,
                "final": second_rule_result,
                "prompt_version": settings.prompt_version,
                "model_version": settings.model_version,
                "retrieval_version": settings.retrieval_version,
                "rule_set_version": settings.rule_set_version,
            },
            revised_text=revised_text,
            final_text="",
            expert_decision="pending",
        )
        message.status = "pending_expert_review" if settings.expert_review_mode == "manual_review_required" else "drafted"
        session.add(message)
        session.add(draft)
        session.commit()
        session.refresh(draft)

        session.add(
            AuditLog(
                thread_id=thread.id,
                message_id=message.id,
                interaction_state_id=interaction.id,
                draft_response_id=draft.id,
                event_type="turn_processed",
                payload={
                    "parse_result": parse_result.model_dump(),
                    "state_after": merged,
                    "selected_action": selection,
                    "retrieved_playbook_ids": draft.selected_playbooks,
                    "draft_text": draft_text,
                    "revised_text": revised_text,
                    "rule_results": draft.rule_check_results,
                },
            )
        )
        session.commit()
        return draft
