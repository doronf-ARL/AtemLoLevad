from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column
from sqlalchemy.dialects.sqlite import JSON
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TimestampedModel(SQLModel):
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Thread(TimestampedModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    patient_id: int = Field(index=True)
    caregiver_id: int = Field(index=True)


class PersonModel(TimestampedModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    role: str
    background_story: str = ""
    traits: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    states: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    triggers: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    behavior_patterns: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    risk: dict = Field(default_factory=dict, sa_column=Column(JSON))
    notes: str = ""
    confidence_summary: dict = Field(default_factory=dict, sa_column=Column(JSON))


class InteractionState(TimestampedModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    thread_id: int = Field(index=True)
    patient_id: int = Field(index=True)
    caregiver_id: int = Field(index=True)
    current_trigger: str = ""
    patient_state_snapshot: dict = Field(default_factory=dict, sa_column=Column(JSON))
    caregiver_state_snapshot: dict = Field(default_factory=dict, sa_column=Column(JSON))
    interaction_pattern: str = ""
    risk_snapshot: dict = Field(default_factory=dict, sa_column=Column(JSON))
    decision_need: str = ""
    raw_message_excerpt: str = ""
    structured_observations: dict = Field(default_factory=dict, sa_column=Column(JSON))


class Playbook(TimestampedModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    summary: str
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    applies_when: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    do_items: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    dont_items: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    micro_questions: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    example_response: str = ""
    contraindications: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    escalation_notes: str = ""
    source_type: str = "expert_written"
    status: str = "approved"


class Principle(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    statement: str
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    priority: int = 1
    applies_to: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    exceptions: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    status: str = "approved"


class ConstraintRule(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: str
    condition: str
    enforcement_type: str
    severity: str
    status: str = "active"


class Message(TimestampedModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    thread_id: int = Field(index=True)
    sender_role: str
    content: str
    status: str = "received"


class DraftResponse(TimestampedModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    message_id: int = Field(index=True)
    interaction_state_id: int = Field(index=True)
    selected_action: str
    selected_playbooks: list[int] = Field(default_factory=list, sa_column=Column(JSON))
    draft_text: str
    rule_check_results: dict = Field(default_factory=dict, sa_column=Column(JSON))
    revised_text: str = ""
    final_text: str = ""
    expert_decision: str = "pending"
    expert_edits: str = ""


class ExpertFeedback(TimestampedModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    draft_response_id: int = Field(index=True)
    decision: str
    edited_text: str = ""
    comment: str = ""
    new_rule_suggestion: str = ""
    new_playbook_suggestion: str = ""


class AuditLog(TimestampedModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    thread_id: int = Field(index=True)
    message_id: int = Field(index=True)
    interaction_state_id: int = Field(index=True)
    draft_response_id: int = Field(index=True)
    event_type: str
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON))


class AppSettings(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    llm_provider: str = "openai"
    llm_tier: str = "low_cost"
    llm_model: str = "gpt-5-mini"
