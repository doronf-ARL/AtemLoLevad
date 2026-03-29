from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.core.llm_catalog import resolve_model


@dataclass
class PatientTemplateDraft:
    name: str
    background_story: str
    notes: str
    traits: str
    states: str
    triggers: str
    behaviors: str
    risk_level: str
    problem_type: str
    error: str = ""


def _extract_json_block(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in LLM response")
    return json.loads(text[start : end + 1])


def _normalize_template(data: dict, background_story: str, problem_type: str) -> PatientTemplateDraft:
    return PatientTemplateDraft(
        name=data.get("name", "Simulated Patient"),
        background_story=background_story,
        notes=data.get("notes", ""),
        traits=", ".join(data.get("traits", [])),
        states=", ".join(data.get("states", [])),
        triggers=", ".join(data.get("triggers", [])),
        behaviors=", ".join(data.get("behaviors", [])),
        risk_level=data.get("risk_level", "low"),
        problem_type=problem_type,
    )


class PatientTemplateService:
    def random_patient(self, problem_type: str) -> PatientTemplateDraft:
        profiles = {
            "PTSD": [
                {
                    "name": "Amit",
                    "background_story": "Amit completed reserve duty near the Gaza border. Since returning home, sudden bangs and emergency alerts leave him frozen and irritable. His partner notices that he avoids crowded places and stops talking after triggers.",
                    "notes": "War-related trigger sensitivity and shutdown after sudden noises.",
                    "traits": "guarded, responsible, exhausted",
                    "states": "hyperarousal, withdrawal",
                    "triggers": "loud_noise_trigger, war_reminder_trigger",
                    "behaviors": "freezing, pursue_withdraw_pattern",
                    "risk_level": "medium",
                },
                {
                    "name": "Noam",
                    "background_story": "Noam was exposed to repeated rocket fire. He sleeps lightly, startles at door slams, and sometimes leaves family gatherings abruptly when the room becomes noisy.",
                    "notes": "Acute startle response with avoidance around crowd and noise.",
                    "traits": "vigilant, ashamed, protective",
                    "states": "hyperarousal, shame",
                    "triggers": "loud_noise_trigger, war_reminder_trigger",
                    "behaviors": "withdrawal, freezing",
                    "risk_level": "medium",
                },
            ],
            "eating_disorder": [
                {
                    "name": "Maya",
                    "background_story": "Maya has become increasingly rigid around food and exercise over the last year. Meals with family often end in conflict, and she becomes distressed when plans change or when others comment on what she is eating.",
                    "notes": "High rigidity around meals with frequent conflict and shame afterwards.",
                    "traits": "perfectionistic, secretive, driven",
                    "states": "fear, shame",
                    "triggers": "meal_change_trigger, body_comment_trigger",
                    "behaviors": "withdrawal, irritability",
                    "risk_level": "medium",
                },
                {
                    "name": "Lior",
                    "background_story": "Lior has started skipping shared meals and insists on strict food rules. When family members push him to eat more, he becomes angry and leaves the room.",
                    "notes": "Meal-related rigidity with interpersonal escalation when pressured.",
                    "traits": "controlling, anxious, isolated",
                    "states": "fear, irritability",
                    "triggers": "meal_pressure_trigger, body_comment_trigger",
                    "behaviors": "withdrawal, pursue_withdraw_pattern",
                    "risk_level": "medium",
                },
            ],
        }
        normalized_problem = "eating_disorder" if problem_type == "eating_disorder" else "PTSD"
        profile = random.choice(profiles[normalized_problem])
        return PatientTemplateDraft(problem_type=normalized_problem, error="", **profile)

    def fill_from_story(self, provider: str, tier: str, background_story: str, problem_type: str) -> PatientTemplateDraft:
        if not background_story.strip():
            return PatientTemplateDraft(
                name="",
                background_story="",
                notes="",
                traits="",
                states="",
                triggers="",
                behaviors="",
                risk_level="low",
                problem_type=problem_type,
                error="Background story is required.",
            )

        model = resolve_model(provider, tier)
        prompt = (
            "You are filling a structured patient intake template for an internal caregiver-support tool. "
            f"Primary problem type: {problem_type}. "
            "Return strict JSON with keys: name, notes, traits, states, triggers, behaviors, risk_level. "
            "Each of traits, states, triggers, behaviors must be a short array of labels. "
            "risk_level must be one of low, medium, high. "
            "Do not include markdown."
        )

        if provider == "openai":
            text = self._call_openai(model, prompt, background_story)
        elif provider == "gemini":
            text = self._call_gemini(model, prompt, background_story)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        data = _extract_json_block(text)
        return _normalize_template(data, background_story, problem_type)

    def _call_openai(self, model: str, instructions: str, background_story: str) -> str:
        api_key = os.getenv(settings.openai_api_key_env)
        if not api_key:
            raise ValueError(f"Missing {settings.openai_api_key_env}")
        response = httpx.post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "input": [
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": background_story},
                ],
            },
            timeout=45.0,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("output_text"):
            return payload["output_text"]
        output = payload.get("output", [])
        texts: list[str] = []
        for item in output:
            for content in item.get("content", []):
                text = content.get("text")
                if text:
                    texts.append(text)
        if not texts:
            raise ValueError("OpenAI response did not contain text output")
        return "\n".join(texts)

    def _call_gemini(self, model: str, instructions: str, background_story: str) -> str:
        api_key = os.getenv(settings.gemini_api_key_env)
        if not api_key:
            raise ValueError(f"Missing {settings.gemini_api_key_env}")
        response = httpx.post(
            f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent",
            params={"key": api_key},
            headers={"Content-Type": "application/json"},
            json={
                "systemInstruction": {"parts": [{"text": instructions}]},
                "contents": [{"parts": [{"text": background_story}]}],
            },
            timeout=45.0,
        )
        response.raise_for_status()
        payload = response.json()
        candidates = payload.get("candidates", [])
        if not candidates:
            raise ValueError("Gemini response did not contain candidates")
        parts = candidates[0].get("content", {}).get("parts", [])
        texts = [part.get("text", "") for part in parts if part.get("text")]
        if not texts:
            raise ValueError("Gemini response did not contain text output")
        return "\n".join(texts)
