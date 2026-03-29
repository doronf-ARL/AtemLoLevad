from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.core.config import settings
from app.core.llm_catalog import LLM_OPTIONS, resolve_model
from app.db.models import AppSettings, AuditLog, DraftResponse, InteractionState, Message, PersonModel, Thread
from app.db.session import get_session
from app.domain.schemas.common import ExpertDecisionRequest, ExpertEditRequest, MessageCreate, PersonCreate, ThreadCreate
from app.domain.services.expert_review import ExpertReviewService
from app.domain.services.patient_templates import PatientTemplateDraft, PatientTemplateService
from app.domain.services.pipeline import PipelineService


router = APIRouter()
templates = Jinja2Templates(directory=str(settings.base_dir / "app" / "ui" / "templates"))
pipeline = PipelineService()
expert_review = ExpertReviewService()
patient_template_service = PatientTemplateService()


EMPTY_PATIENT_FORM = {
    "name": "",
    "background_story": "",
    "notes": "",
    "traits": "",
    "states": "",
    "triggers": "",
    "behaviors": "",
    "risk_level": "low",
    "problem_type": "PTSD",
    "error": "",
}


def to_dict(model):
    if not model:
        return None
    data = {}
    for column in model.__table__.columns:
        value = getattr(model, column.name)
        data[column.name] = value.isoformat() if hasattr(value, "isoformat") else value
    return data


def labels_to_items(raw: str) -> list[dict]:
    items: list[dict] = []
    for token in [part.strip() for part in raw.split(",") if part.strip()]:
        items.append({"label": token.lower().replace(" ", "_"), "intensity": "medium", "confidence": 0.6, "evidence": "ui_simulated"})
    return items


def thread_view(session: Session, thread: Thread) -> dict:
    patient = session.get(PersonModel, thread.patient_id)
    caregiver = session.get(PersonModel, thread.caregiver_id)
    messages = session.exec(select(Message).where(Message.thread_id == thread.id).order_by(Message.id)).all()
    drafts = session.exec(select(DraftResponse).join(Message, DraftResponse.message_id == Message.id).where(Message.thread_id == thread.id).order_by(DraftResponse.id.desc())).all()
    return {"id": thread.id, "title": thread.title, "patient": patient, "caregiver": caregiver, "messages": messages, "drafts": drafts, "created_at": thread.created_at}


def get_or_create_app_settings(session: Session) -> AppSettings:
    record = session.exec(select(AppSettings).order_by(AppSettings.id)).first()
    if record:
        return record
    record = AppSettings()
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def current_llm_state(session: Session) -> dict:
    app_state = get_or_create_app_settings(session)
    return {
        "provider": app_state.llm_provider,
        "tier": app_state.llm_tier,
        "model": app_state.llm_model,
        "options": LLM_OPTIONS,
    }


def draft_to_form_state(draft: PatientTemplateDraft) -> dict:
    return {
        "name": draft.name,
        "background_story": draft.background_story,
        "notes": draft.notes,
        "traits": draft.traits,
        "states": draft.states,
        "triggers": draft.triggers,
        "behaviors": draft.behaviors,
        "risk_level": draft.risk_level,
        "problem_type": draft.problem_type,
        "error": draft.error,
    }


def render_patients_page(request: Request, session: Session, form_state: dict | None = None) -> HTMLResponse:
    patients = session.exec(select(PersonModel).where(PersonModel.role == "patient").order_by(PersonModel.id)).all()
    return templates.TemplateResponse(request, "patients.html", {"patients": patients, "form_state": form_state or dict(EMPTY_PATIENT_FORM), "llm": current_llm_state(session)})


@router.get("/", response_class=HTMLResponse)
def home(request: Request, session: Session = Depends(get_session)):
    patient_count = len(session.exec(select(PersonModel).where(PersonModel.role == "patient")).all())
    caregiver_count = len(session.exec(select(PersonModel).where(PersonModel.role == "caregiver")).all())
    thread_count = len(session.exec(select(Thread)).all())
    pending_count = len(session.exec(select(DraftResponse).where(DraftResponse.expert_decision == "pending")).all())
    return templates.TemplateResponse(request, "index.html", {"patient_count": patient_count, "caregiver_count": caregiver_count, "thread_count": thread_count, "pending_count": pending_count, "llm": current_llm_state(session)})


@router.post("/settings/llm")
def update_llm_settings(provider: str = Form(...), tier: str = Form(...), session: Session = Depends(get_session)):
    app_state = get_or_create_app_settings(session)
    app_state.llm_provider = provider
    app_state.llm_tier = tier
    app_state.llm_model = resolve_model(provider, tier)
    session.add(app_state)
    session.commit()
    return RedirectResponse(url="/", status_code=303)


@router.get("/patients", response_class=HTMLResponse)
def patients_page(request: Request, session: Session = Depends(get_session)):
    return render_patients_page(request, session)


@router.post("/patients/create", response_class=HTMLResponse)
def create_patient_form(request: Request, name: str = Form(...), background_story: str = Form(""), notes: str = Form(""), traits: str = Form(""), states: str = Form(""), triggers: str = Form(""), behaviors: str = Form(""), risk_level: str = Form("low"), problem_type: str = Form("PTSD"), session: Session = Depends(get_session)):
    patient = PersonModel(name=name, role="patient", background_story=background_story, notes=notes, traits=labels_to_items(traits), states=labels_to_items(states), triggers=labels_to_items(triggers), behavior_patterns=labels_to_items(behaviors), risk={"level": risk_level}, confidence_summary={"source": "ui_simulated", "problem_type": problem_type})
    session.add(patient)
    session.commit()
    session.refresh(patient)
    return RedirectResponse(url=f"/patients/{patient.id}", status_code=303)


@router.post("/patients/randomize", response_class=HTMLResponse)
def randomize_patient_form(request: Request, problem_type: str = Form("PTSD"), session: Session = Depends(get_session)):
    draft = patient_template_service.random_patient(problem_type)
    return render_patients_page(request, session, draft_to_form_state(draft))


@router.post("/patients/fill-template", response_class=HTMLResponse)
def fill_patient_template_form(request: Request, name: str = Form(""), background_story: str = Form(""), notes: str = Form(""), traits: str = Form(""), states: str = Form(""), triggers: str = Form(""), behaviors: str = Form(""), risk_level: str = Form("low"), problem_type: str = Form("PTSD"), session: Session = Depends(get_session)):
    app_state = get_or_create_app_settings(session)
    try:
        draft = patient_template_service.fill_from_story(app_state.llm_provider, app_state.llm_tier, background_story, problem_type)
        form_state = draft_to_form_state(draft)
        if name.strip():
            form_state["name"] = name
    except Exception as exc:
        form_state = {"name": name, "background_story": background_story, "notes": notes, "traits": traits, "states": states, "triggers": triggers, "behaviors": behaviors, "risk_level": risk_level, "problem_type": problem_type, "error": str(exc)}
    return render_patients_page(request, session, form_state)


@router.get("/patients/{person_id}", response_class=HTMLResponse)
def patient_detail(person_id: int, request: Request, session: Session = Depends(get_session)):
    patient = session.get(PersonModel, person_id)
    if not patient or patient.role != "patient":
        raise HTTPException(status_code=404, detail="Patient not found")
    linked_threads = session.exec(select(Thread).where(Thread.patient_id == patient.id).order_by(Thread.id.desc())).all()
    return templates.TemplateResponse(request, "patient_detail.html", {"patient": patient, "linked_threads": linked_threads})


@router.get("/caregivers", response_class=HTMLResponse)
def caregivers_page(request: Request, session: Session = Depends(get_session)):
    caregivers = session.exec(select(PersonModel).where(PersonModel.role == "caregiver").order_by(PersonModel.id)).all()
    return templates.TemplateResponse(request, "caregivers.html", {"caregivers": caregivers})


@router.post("/caregivers/create", response_class=HTMLResponse)
def create_caregiver_form(request: Request, name: str = Form(...), notes: str = Form(""), traits: str = Form(""), states: str = Form(""), behaviors: str = Form(""), risk_level: str = Form("low"), session: Session = Depends(get_session)):
    caregiver = PersonModel(name=name, role="caregiver", notes=notes, traits=labels_to_items(traits), states=labels_to_items(states), triggers=[], behavior_patterns=labels_to_items(behaviors), risk={"level": risk_level}, confidence_summary={"source": "ui_simulated"})
    session.add(caregiver)
    session.commit()
    session.refresh(caregiver)
    return RedirectResponse(url=f"/caregivers/{caregiver.id}", status_code=303)


@router.get("/caregivers/{person_id}", response_class=HTMLResponse)
def caregiver_detail(person_id: int, request: Request, session: Session = Depends(get_session)):
    caregiver = session.get(PersonModel, person_id)
    if not caregiver or caregiver.role != "caregiver":
        raise HTTPException(status_code=404, detail="Caregiver not found")
    linked_threads = session.exec(select(Thread).where(Thread.caregiver_id == caregiver.id).order_by(Thread.id.desc())).all()
    return templates.TemplateResponse(request, "caregiver_detail.html", {"caregiver": caregiver, "linked_threads": linked_threads})


@router.get("/messages", response_class=HTMLResponse)
def messages_page(request: Request, session: Session = Depends(get_session)):
    threads = session.exec(select(Thread).order_by(Thread.id.desc())).all()
    patients = session.exec(select(PersonModel).where(PersonModel.role == "patient").order_by(PersonModel.id)).all()
    caregivers = session.exec(select(PersonModel).where(PersonModel.role == "caregiver").order_by(PersonModel.id)).all()
    thread_cards = [thread_view(session, thread) for thread in threads]
    return templates.TemplateResponse(request, "messages.html", {"threads": thread_cards, "patients": patients, "caregivers": caregivers})


@router.post("/messages/threads/create", response_class=HTMLResponse)
def create_thread_form(request: Request, title: str = Form(...), patient_id: int = Form(...), caregiver_id: int = Form(...), session: Session = Depends(get_session)):
    patient = session.get(PersonModel, patient_id)
    caregiver = session.get(PersonModel, caregiver_id)
    if not patient or patient.role != "patient":
        raise HTTPException(status_code=400, detail="Valid patient is required")
    if not caregiver or caregiver.role != "caregiver":
        raise HTTPException(status_code=400, detail="Valid caregiver is required")
    thread = Thread(title=title, patient_id=patient_id, caregiver_id=caregiver_id)
    session.add(thread)
    session.commit()
    session.refresh(thread)
    return RedirectResponse(url=f"/messages/threads/{thread.id}", status_code=303)


@router.get("/messages/threads/{thread_id}", response_class=HTMLResponse)
def thread_detail(thread_id: int, request: Request, session: Session = Depends(get_session)):
    thread = session.get(Thread, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return templates.TemplateResponse(request, "thread_detail.html", {"thread": thread_view(session, thread)})


@router.post("/messages/threads/{thread_id}/send", response_class=HTMLResponse)
def send_message_form(thread_id: int, request: Request, content: str = Form(...), session: Session = Depends(get_session)):
    thread = session.get(Thread, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    message = Message(thread_id=thread.id, sender_role="caregiver", content=content)
    session.add(message)
    session.commit()
    session.refresh(message)
    pipeline.process_message(session, thread, message)
    return RedirectResponse(url=f"/messages/threads/{thread.id}", status_code=303)


@router.get("/threads")
def list_threads(session: Session = Depends(get_session)):
    return [to_dict(thread) for thread in session.exec(select(Thread).order_by(Thread.id)).all()]


@router.post("/threads")
def create_thread(payload: ThreadCreate, session: Session = Depends(get_session)):
    thread = Thread(**payload.model_dump())
    session.add(thread)
    session.commit()
    session.refresh(thread)
    return to_dict(thread)


@router.get("/threads/{thread_id}")
def get_thread(thread_id: int, session: Session = Depends(get_session)):
    thread = session.get(Thread, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return to_dict(thread)


@router.get("/threads/{thread_id}/messages")
def list_messages(thread_id: int, session: Session = Depends(get_session)):
    messages = session.exec(select(Message).where(Message.thread_id == thread_id).order_by(Message.id)).all()
    return [to_dict(message) for message in messages]


@router.post("/threads/{thread_id}/messages")
def create_message(thread_id: int, payload: MessageCreate, session: Session = Depends(get_session)):
    thread = session.get(Thread, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    message = Message(thread_id=thread_id, sender_role=payload.sender_role, content=payload.content)
    session.add(message)
    session.commit()
    session.refresh(message)
    draft = pipeline.process_message(session, thread, message)
    session.refresh(message)
    session.refresh(draft)
    return {"message": to_dict(message), "draft": to_dict(draft)}


@router.get("/api/patients")
def api_list_patients(session: Session = Depends(get_session)):
    patients = session.exec(select(PersonModel).where(PersonModel.role == "patient").order_by(PersonModel.id)).all()
    return [to_dict(patient) for patient in patients]


@router.post("/api/patients")
def api_create_patient(payload: PersonCreate, session: Session = Depends(get_session)):
    if payload.role != "patient":
        raise HTTPException(status_code=400, detail="Role must be patient")
    patient = PersonModel(**payload.model_dump())
    session.add(patient)
    session.commit()
    session.refresh(patient)
    return to_dict(patient)


@router.get("/api/caregivers")
def api_list_caregivers(session: Session = Depends(get_session)):
    caregivers = session.exec(select(PersonModel).where(PersonModel.role == "caregiver").order_by(PersonModel.id)).all()
    return [to_dict(caregiver) for caregiver in caregivers]


@router.post("/api/caregivers")
def api_create_caregiver(payload: PersonCreate, session: Session = Depends(get_session)):
    if payload.role != "caregiver":
        raise HTTPException(status_code=400, detail="Role must be caregiver")
    caregiver = PersonModel(**payload.model_dump())
    session.add(caregiver)
    session.commit()
    session.refresh(caregiver)
    return to_dict(caregiver)


@router.get("/expert/drafts/pending")
def pending_drafts(session: Session = Depends(get_session)):
    drafts = session.exec(select(DraftResponse).where(DraftResponse.expert_decision == "pending").order_by(DraftResponse.id.desc())).all()
    return [to_dict(draft) for draft in drafts]


@router.get("/expert/drafts/{draft_id}")
def get_draft(draft_id: int, session: Session = Depends(get_session)):
    draft = session.get(DraftResponse, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return to_dict(draft)


@router.post("/expert/drafts/{draft_id}/approve")
def approve_draft(draft_id: int, payload: ExpertDecisionRequest, session: Session = Depends(get_session)):
    draft = session.get(DraftResponse, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    result = expert_review.approve(session, draft, payload.comment)
    session.refresh(result)
    return to_dict(result)


@router.post("/expert/drafts/{draft_id}/edit")
def edit_draft(draft_id: int, payload: ExpertEditRequest, session: Session = Depends(get_session)):
    draft = session.get(DraftResponse, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    result = expert_review.edit(session, draft, payload.edited_text, payload.comment)
    session.refresh(result)
    return to_dict(result)


@router.post("/expert/drafts/{draft_id}/reject")
def reject_draft(draft_id: int, payload: ExpertDecisionRequest, session: Session = Depends(get_session)):
    draft = session.get(DraftResponse, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    result = expert_review.reject(session, draft, payload.comment)
    session.refresh(result)
    return to_dict(result)


@router.get("/expert", response_class=HTMLResponse)
def expert_inbox(request: Request, session: Session = Depends(get_session)):
    drafts = session.exec(select(DraftResponse).where(DraftResponse.expert_decision == "pending").order_by(DraftResponse.id.desc())).all()
    enriched = []
    for draft in drafts:
        message = session.get(Message, draft.message_id)
        thread = session.get(Thread, message.thread_id) if message else None
        enriched.append({"draft": draft, "message": message, "thread": thread})
    return templates.TemplateResponse(request, "expert_inbox.html", {"drafts": enriched})


@router.get("/expert/drafts/{draft_id}/review", response_class=HTMLResponse)
def expert_review_page(draft_id: int, request: Request, session: Session = Depends(get_session)):
    draft = session.get(DraftResponse, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    message = session.get(Message, draft.message_id)
    interaction = session.get(InteractionState, draft.interaction_state_id)
    thread = session.get(Thread, message.thread_id) if message else None
    patient = session.get(PersonModel, thread.patient_id) if thread else None
    caregiver = session.get(PersonModel, thread.caregiver_id) if thread else None
    return templates.TemplateResponse(request, "draft_review.html", {"draft": draft, "message": message, "interaction": interaction, "thread": thread, "patient": patient, "caregiver": caregiver})


@router.post("/expert/drafts/{draft_id}/review/approve", response_class=HTMLResponse)
def approve_draft_form(draft_id: int, request: Request, comment: str = Form(""), session: Session = Depends(get_session)):
    draft = session.get(DraftResponse, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    expert_review.approve(session, draft, comment)
    return RedirectResponse(url=f"/messages/threads/{session.get(Message, draft.message_id).thread_id}", status_code=303)


@router.post("/expert/drafts/{draft_id}/review/edit", response_class=HTMLResponse)
def edit_draft_form(draft_id: int, request: Request, edited_text: str = Form(...), comment: str = Form(""), session: Session = Depends(get_session)):
    draft = session.get(DraftResponse, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    expert_review.edit(session, draft, edited_text, comment)
    return RedirectResponse(url=f"/messages/threads/{session.get(Message, draft.message_id).thread_id}", status_code=303)


@router.post("/expert/drafts/{draft_id}/review/reject", response_class=HTMLResponse)
def reject_draft_form(draft_id: int, request: Request, comment: str = Form(""), session: Session = Depends(get_session)):
    draft = session.get(DraftResponse, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    expert_review.reject(session, draft, comment)
    return RedirectResponse(url=f"/messages/threads/{session.get(Message, draft.message_id).thread_id}", status_code=303)


@router.get("/debug", response_class=HTMLResponse)
def debug_view(request: Request, session: Session = Depends(get_session)):
    logs = session.exec(select(AuditLog).order_by(AuditLog.id.desc())).all()
    return templates.TemplateResponse(request, "debug_logs.html", {"logs": logs})
