from __future__ import annotations

from sqlmodel import Session

from app.db.models import DraftResponse, ExpertFeedback, Message


class ExpertReviewService:
    def approve(self, session: Session, draft: DraftResponse, comment: str = "") -> DraftResponse:
        draft.expert_decision = "approve"
        draft.final_text = draft.revised_text or draft.draft_text
        session.add(ExpertFeedback(draft_response_id=draft.id, decision="approve", comment=comment))
        message = session.get(Message, draft.message_id)
        if message:
            message.status = "approved"
            session.add(message)
        session.add(draft)
        session.commit()
        session.refresh(draft)
        return draft

    def edit(self, session: Session, draft: DraftResponse, edited_text: str, comment: str = "") -> DraftResponse:
        draft.expert_decision = "edit"
        draft.expert_edits = edited_text
        draft.final_text = edited_text
        session.add(ExpertFeedback(draft_response_id=draft.id, decision="edit", edited_text=edited_text, comment=comment))
        message = session.get(Message, draft.message_id)
        if message:
            message.status = "approved"
            session.add(message)
        session.add(draft)
        session.commit()
        session.refresh(draft)
        return draft

    def reject(self, session: Session, draft: DraftResponse, comment: str = "") -> DraftResponse:
        draft.expert_decision = "reject"
        session.add(ExpertFeedback(draft_response_id=draft.id, decision="reject", comment=comment))
        message = session.get(Message, draft.message_id)
        if message:
            message.status = "rejected"
            session.add(message)
        session.add(draft)
        session.commit()
        session.refresh(draft)
        return draft
