# Caregiver Support AI MVP

This project is a local prototype of a caregiver-support assistant for family members or close friends supporting a distressed person. It uses explicit state, constrained action selection, playbook retrieval, rule checks, turn logging, and an expert review gate.

## Current UX

The app starts with empty data.

You create simulated records directly in the browser:

- `/patients`: add and inspect patients
- `/caregivers`: add and inspect caregivers
- `/messages`: create threads that connect one patient and one caregiver, then send simulated caregiver messages
- `/expert`: review generated drafts
- `/debug`: inspect audit logs

The patient form also supports:

- `Gen Random`: creates a random simulated patient template for the selected problem type (`PTSD` or `Eating Disorder`)
- `Fill Template`: sends the free-text background story to the currently selected LLM and fills the patient slots from the response

## LLM Selection

The home page stores a global LLM choice for template filling.

Supported options:

- OpenAI low cost: `gpt-5-mini`
- OpenAI best: `gpt-5`
- Gemini low cost: `gemini-2.5-flash`
- Gemini best: `gemini-2.5-pro`

Expected environment variables:

- `OPENAI_API_KEY`
- `GEMINI_API_KEY`

## Architecture Summary

The backend is a FastAPI app with SQLite storage via SQLModel. The message pipeline is deterministic and inspectable:

1. Parse caregiver text into structured observations
2. Merge into structured case state
3. Select one primary action
4. Retrieve relevant playbooks and principles
5. Generate a concise caregiver-facing draft
6. Run explicit Python rule checks and revise once if needed
7. Queue for expert approval
8. Persist logs and artifacts for every turn

## Setup

Requirements:

- Python 3.10+

Install dependencies:

```bash
python -m pip install -e .[dev]
```

Run the app locally:

```bash
uvicorn app.main:app --reload
```

Open:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/patients`
- `http://127.0.0.1:8000/caregivers`
- `http://127.0.0.1:8000/messages`
- `http://127.0.0.1:8000/expert`
- `http://127.0.0.1:8000/debug`

## Render Deploy

This repo now includes [`render.yaml`](/d:/dev/AtemLoLevad/render.yaml) for a simple Render web service.

Deploy steps:

1. Push this repo to GitHub.
2. In Render, create a new Blueprint or Web Service from the repo.
3. Render should pick up `render.yaml` automatically.
4. In the Render dashboard, set any secrets you want to use:
   - `OPENAI_API_KEY`
   - `GEMINI_API_KEY`
5. Deploy.

Render start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Important limitation for demos:

- The app uses local SQLite.
- On Render free web services, the filesystem is ephemeral, so your data may reset on redeploy/restart.
- That is acceptable for a meeting demo, but not for persistent usage.

## Data Model

- `PersonModel`: stores patient or caregiver records, including patient background story
- `Thread`: connects one patient and one caregiver
- `Message`: stores caregiver thread messages
- `InteractionState`: stores inferred state snapshots for each turn
- `DraftResponse`: stores generated drafts and review outcomes
- `AuditLog`: stores pipeline artifacts for inspection
- `AppSettings`: stores the currently selected LLM provider/model tier

## API Highlights

- `GET /threads`
- `POST /threads`
- `POST /threads/{id}/messages`
- `GET /api/patients`
- `POST /api/patients`
- `GET /api/caregivers`
- `POST /api/caregivers`
- `GET /expert/drafts/pending`
- `POST /expert/drafts/{id}/approve`
- `POST /expert/drafts/{id}/edit`
- `POST /expert/drafts/{id}/reject`
- `GET /debug/logs`

## Testing

Run:

```bash
pytest
```

The tests cover:

- rule checker
- state merge logic
- retrieval ranking
- action selection fallback
- empty-state startup
- LLM selection persistence
- random patient template UI flow
- LLM template fill UI flow
- patient/caregiver/thread creation
- message-in to draft-out integration
- expert edit flow

## Known Limitations

- The message pipeline still uses deterministic parsing and generation, not a live LLM backend.
- The patient template filler makes live API calls and is only lightly normalized; it does not yet use strict server-side structured outputs.
- Authentication and production safety controls are not implemented.
- The UI is intentionally minimal and internal-facing.
