from __future__ import annotations

from sqlmodel import Session, select

from app.db.models import ConstraintRule, PersonModel, Playbook, Principle, Thread


def seed_data(session: Session) -> None:
    existing = session.exec(select(Thread)).first()
    if existing:
        return

    thread = Thread(title="Seeded PTSD-like caregiver scenario", caregiver_name="Yael", patient_name="Amit")
    session.add(thread)
    session.commit()
    session.refresh(thread)

    patient = PersonModel(
        thread_id=thread.id,
        name="Amit",
        role="patient",
        traits=[{"label": "war_related_ptsd_like_pattern", "confidence": 0.8, "evidence": "seed scenario"}],
        states=[{"label": "hyperarousal", "intensity": "medium", "confidence": 0.6, "evidence": "history"}],
        triggers=[{"label": "loud_noise_trigger", "intensity": "high", "confidence": 0.8, "evidence": "history"}],
        behavior_patterns=[{"label": "withdrawal", "intensity": "medium", "confidence": 0.7, "evidence": "history"}],
        risk={"level": "medium"},
        notes="War-related trigger sensitivity and shutdown after loud sounds.",
        confidence_summary={"overall": 0.75},
    )
    caregiver = PersonModel(
        thread_id=thread.id,
        name="Yael",
        role="caregiver",
        traits=[{"label": "supportive_partner", "confidence": 0.9, "evidence": "seed scenario"}],
        states=[{"label": "caregiver_anxiety", "intensity": "medium", "confidence": 0.65, "evidence": "history"}],
        triggers=[],
        behavior_patterns=[{"label": "caregiver_over_responsibility", "intensity": "medium", "confidence": 0.7, "evidence": "history"}],
        risk={"level": "low"},
        notes="Tends to over-question during acute distress.",
        confidence_summary={"overall": 0.7},
    )
    session.add(patient)
    session.add(caregiver)

    playbooks = [
        Playbook(title="Flashback / high arousal after loud noise", summary="Reduce stimulation and orient the patient to the present.", tags=["ground", "hyperarousal", "loud_noise_trigger"], applies_when=["hyperarousal", "loud_noise_trigger"], do_items=["reduce noise", "use one calm grounding sentence", "slow the pace"], dont_items=["rapid questioning", "confrontation"], micro_questions=["Can you stay nearby and keep it simple?"], example_response="Stay near him, lower the noise, and give one short grounding cue.", contraindications=["extended reasoning demands"], escalation_notes="Escalate if safety risk appears or orientation worsens.", status="approved"),
        Playbook(title="Withdrawal and silence after trigger", summary="Lower interpersonal pressure and allow short, present-focused support.", tags=["reduce_pressure", "withdrawal"], applies_when=["withdrawal", "war_reminder_trigger"], do_items=["pause questions", "offer one low-demand support option"], dont_items=["pressing for explanation"], micro_questions=["Would water or sitting quietly help more right now?"], example_response="Do not chase the story right now; reduce pressure and stay present.", contraindications=["active safety threat"], escalation_notes="Escalate if he becomes unreachable or unsafe.", status="approved"),
        Playbook(title="Caregiver over-questioning during acute distress", summary="Help caregiver stop pursuit and co-regulate first.", tags=["reduce_pressure", "caregiver_over_responsibility", "caregiver_anxiety"], applies_when=["caregiver_anxiety", "pursue_withdraw_pattern"], do_items=["ask fewer questions", "regulate your own pace first"], dont_items=["stacking options", "seeking full explanation"], micro_questions=["Can you shift from questions to one calm statement?"], example_response="Less questioning usually helps more in the acute phase.", contraindications=[], escalation_notes="Escalate if caregiver cannot maintain safety.", status="approved"),
        Playbook(title="When to call clinician / outside help", summary="Escalate when risk or loss of safety exceeds home support.", tags=["escalate", "escalation_needed"], applies_when=["high_risk"], do_items=["contact clinician", "contact emergency services if immediate danger"], dont_items=["manage alone when safety is at risk"], micro_questions=[], example_response="Bring in outside help if there is any immediate danger.", contraindications=[], escalation_notes="Immediate action required for self-harm, violence, or severe disorientation.", status="approved"),
        Playbook(title="Boundary setting during irritability", summary="Keep support and limits in the same calm sentence.", tags=["set_boundary", "irritability"], applies_when=["irritability"], do_items=["use short boundary", "stay calm", "pause if tone escalates"], dont_items=["lecturing", "matching intensity"], micro_questions=[], example_response="I want to stay with you, and I’ll keep talking once we slow this down.", contraindications=["acute danger"], escalation_notes="Escalate if irritability turns violent.", status="approved"),
    ]
    principles = [
        Principle(title="Arousal first", statement="Stabilize arousal before content.", tags=["hyperarousal"], priority=1, applies_to=["ground"]),
        Principle(title="Reduce cognitive load", statement="Use short, simple language in acute distress.", tags=["hyperarousal", "withdrawal"], priority=1, applies_to=["ground", "reduce_pressure"]),
        Principle(title="No confrontation in acute state", statement="Do not push for explanations during acute overload.", tags=["hyperarousal"], priority=1, applies_to=["reduce_pressure"]),
        Principle(title="Follow patient capacity", statement="Match support to what the patient can tolerate right now.", tags=["withdrawal"], priority=2, applies_to=["reduce_pressure"]),
        Principle(title="Support presence over content", statement="Presence is often more useful than discussion during overload.", tags=["withdrawal"], priority=2, applies_to=["validate"]),
        Principle(title="Regulate caregiver first", statement="The caregiver’s pace affects the interaction.", tags=["caregiver_anxiety"], priority=2, applies_to=["reduce_pressure"]),
        Principle(title="Break escalation loops", statement="Interrupt pursue-withdraw cycles with less pressure.", tags=["pursue_withdraw_pattern"], priority=2, applies_to=["reduce_pressure"]),
        Principle(title="Offer actionable micro-steps", statement="One immediate next step is better than many options.", tags=["ground"], priority=2, applies_to=["ground", "validate"]),
        Principle(title="Respect autonomy", statement="Offer support without forcing disclosure.", tags=["withdrawal"], priority=3, applies_to=["reduce_pressure"]),
        Principle(title="Escalate only when needed", statement="Bring in outside help when risk exceeds home support.", tags=["escalation_needed"], priority=1, applies_to=["escalate"]),
    ]
    rules = [
        ConstraintRule(name="Max one question", description="No more than one question in a response.", condition="question_marks <= 1", enforcement_type="block", severity="medium"),
        ConstraintRule(name="No diagnosis as fact", description="Do not state diagnosis as certain fact.", condition="no definitive diagnosis", enforcement_type="block", severity="high"),
        ConstraintRule(name="No confrontation in high arousal", description="Avoid confrontation during acute distress.", condition="if hyperarousal then no confrontational phrasing", enforcement_type="block", severity="high"),
        ConstraintRule(name="Escalation required at high risk", description="High-risk cases must mention outside help.", condition="if risk == high then include escalation wording", enforcement_type="block", severity="high"),
        ConstraintRule(name="Keep response concise", description="Response should remain short and focused.", condition="word_count <= 90", enforcement_type="warn", severity="low"),
    ]
    session.add_all(playbooks + principles + rules)
    session.commit()

