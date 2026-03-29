from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class StateItem(BaseModel):
    label: str
    intensity: str = "medium"
    confidence: float = 0.5
    evidence: str = ""


class ParseResult(BaseModel):
    triggers: list[StateItem] = Field(default_factory=list)
    patient_state_changes: list[StateItem] = Field(default_factory=list)
    caregiver_state_changes: list[StateItem] = Field(default_factory=list)
    behavior_patterns: list[StateItem] = Field(default_factory=list)
    interaction_pattern: str = ""
    risk_estimate: dict[str, Any] = Field(default_factory=dict)
    uncertainty_notes: list[str] = Field(default_factory=list)
    parser_status: str = "ok"


class PersonCreate(BaseModel):
    name: str
    role: str
    background_story: str = ""
    notes: str = ""
    traits: list[dict] = Field(default_factory=list)
    states: list[dict] = Field(default_factory=list)
    triggers: list[dict] = Field(default_factory=list)
    behavior_patterns: list[dict] = Field(default_factory=list)
    risk: dict[str, Any] = Field(default_factory=dict)
    confidence_summary: dict[str, Any] = Field(default_factory=dict)


class ThreadCreate(BaseModel):
    title: str
    caregiver_id: int
    patient_id: int


class MessageCreate(BaseModel):
    content: str
    sender_role: str = "caregiver"


class PlaybookCreate(BaseModel):
    title: str
    summary: str
    tags: list[str] = Field(default_factory=list)
    applies_when: list[str] = Field(default_factory=list)
    do_items: list[str] = Field(default_factory=list)
    dont_items: list[str] = Field(default_factory=list)
    micro_questions: list[str] = Field(default_factory=list)
    example_response: str = ""
    contraindications: list[str] = Field(default_factory=list)
    escalation_notes: str = ""
    source_type: str = "expert_written"
    status: str = "draft"


class PlaybookUpdate(BaseModel):
    title: str | None = None
    summary: str | None = None
    tags: list[str] | None = None
    applies_when: list[str] | None = None
    do_items: list[str] | None = None
    dont_items: list[str] | None = None
    micro_questions: list[str] | None = None
    example_response: str | None = None
    contraindications: list[str] | None = None
    escalation_notes: str | None = None
    source_type: str | None = None
    status: str | None = None


class ExpertDecisionRequest(BaseModel):
    comment: str = ""


class ExpertEditRequest(BaseModel):
    edited_text: str
    comment: str = ""


class ThreadRead(BaseModel):
    id: int
    title: str
    caregiver_id: int
    patient_id: int
    created_at: datetime


class MessageRead(BaseModel):
    id: int
    thread_id: int
    sender_role: str
    content: str
    status: str
    created_at: datetime
