from fastapi.testclient import TestClient

from app.api import routes
from app.domain.services.patient_templates import PatientTemplateDraft
from app.main import create_app


def test_empty_home_and_llm_settings_flow():
    app = create_app()
    with TestClient(app) as client:
        home = client.get("/")
        assert home.status_code == 200
        assert "Start with empty records" in home.text
        assert "gpt-5-mini" in home.text

        update = client.post("/settings/llm", data={"provider": "gemini", "tier": "best"}, follow_redirects=True)
        assert update.status_code == 200
        assert "gemini-2.5-pro" in update.text


def test_patient_template_helpers(monkeypatch):
    app = create_app()
    with TestClient(app) as client:
        random_page = client.post("/patients/randomize", data={"problem_type": "PTSD"})
        assert random_page.status_code == 200
        assert "Background Story" in random_page.text

        def fake_fill(provider, tier, background_story, problem_type):
            return PatientTemplateDraft(
                name="Filled Patient",
                background_story=background_story,
                notes="Filled notes",
                traits="careful, guarded",
                states="hyperarousal",
                triggers="loud_noise_trigger",
                behaviors="withdrawal",
                risk_level="medium",
                problem_type=problem_type,
            )

        monkeypatch.setattr(routes.patient_template_service, "fill_from_story", fake_fill)
        filled_page = client.post(
            "/patients/fill-template",
            data={"background_story": "He came back from reserve duty and startles at loud noises.", "problem_type": "PTSD"},
        )
        assert filled_page.status_code == 200
        assert "Filled Patient" in filled_page.text
        assert "Filled notes" in filled_page.text


def test_message_in_to_draft_out_and_expert_edit_flow():
    app = create_app()
    with TestClient(app) as client:
        patient = client.post("/api/patients", json={"name": "Amit", "role": "patient", "background_story": "", "notes": "simulated", "traits": [], "states": [], "triggers": [], "behavior_patterns": [], "risk": {"level": "low"}, "confidence_summary": {}}).json()
        caregiver = client.post("/api/caregivers", json={"name": "Yael", "role": "caregiver", "background_story": "", "notes": "simulated", "traits": [], "states": [], "triggers": [], "behavior_patterns": [], "risk": {"level": "low"}, "confidence_summary": {}}).json()
        thread = client.post("/threads", json={"title": "Simulated thread", "patient_id": patient["id"], "caregiver_id": caregiver["id"]}).json()

        response = client.post(f"/threads/{thread['id']}/messages", json={"sender_role": "caregiver", "content": "After a loud bang he froze and I keep asking what happened but he goes silent."})
        assert response.status_code == 200
        payload = response.json()
        assert payload["draft"]["selected_action"] in {"ground", "reduce_pressure"}
        assert payload["draft"]["expert_decision"] == "pending"

        draft_id = payload["draft"]["id"]
        edit_response = client.post(f"/expert/drafts/{draft_id}/edit", json={"edited_text": "Stay close, keep it simple, and reduce noise around him.", "comment": "Tighter phrasing"})
        assert edit_response.status_code == 200
        assert edit_response.json()["final_text"] == "Stay close, keep it simple, and reduce noise around him."
