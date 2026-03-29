# Codex Implementation Spec – Caregiver Support AI

## 1. Purpose
Build a working prototype of a caregiver-support agent for family members and close friends of a distressed person, initially focused on war-related PTSD scenarios in Israel.

This system is **not** a therapist for the patient.
It is a **guided support assistant for the caregiver**, with strong expert oversight.

The prototype should prioritize:
- clarity
- modularity
- inspectability
- logging
- easy iteration
- future migration toward more structured knowledge and partial automation

This spec is intended for implementation by Codex inside VSCode.

---

## 2. Product Goal
A caregiver sends a message describing a difficult situation with the patient.
The system:
1. interprets the message,
2. updates a structured case state,
3. selects a recommended action,
4. retrieves relevant psychological guidance,
5. drafts a response,
6. checks the response against explicit rules,
7. optionally sends to expert for review,
8. returns final text to caregiver.

The first version should be a strong internal prototype, not a polished production system.

---

## 3. High-Level Design Philosophy
Do **not** build a free-form chatbot over documents.
Do **not** build a rigid classical expert system.

Build a hybrid system with:
- structured state
- structured knowledge units
- constrained generation
- explicit rule checks
- full logging
- human review hooks

Guiding principle:
**State and constraints are explicit. Language is generated, not trusted.**

---

## 4. Core Pipeline
For each caregiver message `x_t`:

1. Read prior case state `s_(t-1)`
2. Parse caregiver message into structured observations
3. Update current case state `s_t`
4. Infer action type `a_t`
5. Retrieve 1 to 3 relevant knowledge units `K_t`
6. Generate draft response `y_t`
7. Run rule checker on `y_t`
8. If rule violation, revise or regenerate
9. If expert-review mode is enabled, queue draft for expert
10. Store all artifacts in logs
11. Return final response

---

## 5. MVP Scope
The MVP should support:
- one patient per caregiver thread
- one caregiver user role
- one supervising expert role
- text-only interaction
- structured internal state
- playbook retrieval
- explicit rule checker
- optional expert approval before send

Do **not** implement at MVP stage:
- voice
- multi-expert collaboration
- advanced diagnosis engine
- full knowledge graph
- RL or DPO training
- autonomous therapy planning

---

## 6. Recommended Tech Stack
Codex may adapt if needed, but start with:

### Backend
- Python 3.11+
- FastAPI
- Pydantic
- SQLModel or SQLAlchemy
- SQLite for local prototype, easy migration to Postgres later

### Frontend
Either:
- simple React frontend, or
- minimal admin pages using FastAPI templates if speed matters

### LLM Layer
Abstract LLM provider behind interface.
Need support for:
- structured parsing
- state update prompt
- action selection prompt
- response generation prompt
- critique / revision prompt

### Retrieval
For MVP, prefer hybrid:
- structured tag filtering first
- optional embedding similarity second

### Background Jobs
Optional, only if needed:
- Celery or lightweight async queue

### Dev Tooling
- pytest
- mypy if practical
- Ruff or equivalent linter
- seed scripts for example data

---

## 7. Core Domain Objects

### 7.1 PersonModel
Shared schema for both patient and caregiver.

Fields:
- `id`
- `role` (`patient` or `caregiver`)
- `traits`
- `states`
- `triggers`
- `behavior_patterns`
- `risk`
- `notes`
- `confidence_summary`
- timestamps

Traits and states should be represented in structured form, not only free text.

#### Example trait/state values
Use normalized labels with optional confidence or intensity:
- low / medium / high
- or numeric confidence in `[0,1]`

At MVP, keep implementation simple:
- store canonical label
- store confidence float
- store supporting evidence text snippets

---

### 7.2 InteractionState
Represents the current relationship event and inferred interaction dynamics.

Fields:
- `id`
- `thread_id`
- `patient_id`
- `caregiver_id`
- `current_trigger`
- `patient_state_snapshot`
- `caregiver_state_snapshot`
- `interaction_pattern`
- `risk_snapshot`
- `decision_need`
- `raw_message_excerpt`
- `structured_observations`
- timestamps

This is the evolving case state used by the system.

---

### 7.3 Playbook
Core structured knowledge unit.

A playbook is a reusable guidance object for a class of situations.

Fields:
- `id`
- `title`
- `summary`
- `tags`
- `applies_when`
- `do_items`
- `dont_items`
- `micro_questions`
- `example_response`
- `contraindications`
- `escalation_notes`
- `source_type` (`expert_written`, `expert_derived`, `case_derived`)
- `status` (`draft`, `approved`, `archived`)
- timestamps

Examples:
- flashback / high arousal
- withdrawal after trigger
- caregiver over-questioning
- boundary setting during irritability

Important:
Playbooks are **not** long documents.
They are concise, explicit, structured guidance units.

---

### 7.4 Principle
General psychological principle, more abstract than a playbook.

Fields:
- `id`
- `title`
- `statement`
- `tags`
- `priority`
- `applies_to`
- `exceptions`
- `status`

Examples:
- arousal first
- reduce cognitive load
- no confrontation in acute state
- support presence over content

Principles may be linked to playbooks.

---

### 7.5 ConstraintRule
Hard system rule.

Fields:
- `id`
- `name`
- `description`
- `condition`
- `enforcement_type`
- `severity`
- `status`

Examples:
- max one question per response
- mandatory escalation if certain risk threshold
- do not state diagnosis as fact
- do not recommend confrontation in acute high-arousal state

MVP implementation may keep condition logic in Python code, with DB-backed metadata.

---

### 7.6 Message
Stores inbound and outbound messages.

Fields:
- `id`
- `thread_id`
- `sender_role`
- `content`
- `status`
- timestamps

Statuses may include:
- received
- parsed
- drafted
- pending_expert_review
- approved
- sent
- rejected

---

### 7.7 DraftResponse
Stores generated drafts and revisions.

Fields:
- `id`
- `message_id`
- `interaction_state_id`
- `selected_action`
- `selected_playbooks`
- `draft_text`
- `rule_check_results`
- `revised_text`
- `final_text`
- `expert_decision`
- `expert_edits`
- timestamps

This object is important for future learning.

---

### 7.8 ExpertFeedback
Stores expert supervision traces.

Fields:
- `id`
- `draft_response_id`
- `decision` (`approve`, `edit`, `reject`, `replace`)
- `edited_text`
- `comment`
- `new_rule_suggestion`
- `new_playbook_suggestion`
- timestamps

---

## 8. Canonical Concept Layer
Do not allow uncontrolled concept drift.

Implement a **controlled concept registry**.

Examples of canonical concepts:
- hyperarousal
- fear
- shame
- irritability
- withdrawal
- freezing
- dissociation_like
- caregiver_anxiety
- caregiver_over_responsibility
- loud_noise_trigger
- war_reminder_trigger
- pursue_withdraw_pattern
- grounding
- reduce_pressure
- escalation_needed

The LLM may propose concepts, but the system should map them to canonical labels whenever possible.

MVP approach:
- maintain a registry file or DB table of allowed concepts
- use parser prompts to select from known concepts first
- allow tentative free-text note only in a separate field

---

## 9. State Representation Strategy
Use structured templates with soft values.

Do **not** require complete formalization.
Do **not** require theorem proving.

Recommended representation:
- canonical label
- value or intensity
- confidence
- evidence snippet

Example state item:
- label: `hyperarousal`
- intensity: `high`
- confidence: `0.82`
- evidence: `"suddenly just froze" after loud bang`

This should be easy to inspect and update.

---

## 10. Action Space
Do not generate text directly without choosing an action.

Define small discrete action set for MVP:
- `validate`
- `ground`
- `reduce_pressure`
- `ask_clarifying_question`
- `set_boundary`
- `monitor_and_watch`
- `escalate`

A response may have one primary action and one secondary action, but keep implementation simple at first.

For MVP:
- choose exactly one primary action
- optionally attach one micro-question

---

## 11. Parsing Layer
Need a module that transforms caregiver text into structured observations.

### Input
- caregiver message text
- prior patient model
- prior caregiver model
- prior interaction state

### Output
Structured parsing object with:
- extracted trigger(s)
- inferred patient state changes
- inferred caregiver state changes
- observed behavior patterns
- inferred interaction pattern
- risk estimate
- uncertainty notes

### Implementation note
Use LLM structured output with strict schema.
If structured parsing fails, retry once with repair prompt.
If still fails, store fallback with error flag.

---

## 12. State Update Layer
This module merges previous state and current structured observations.

Responsibilities:
- preserve persistent traits
- update dynamic states
- add new triggers if relevant
- revise confidence scores
- avoid duplication

Implementation approach:
- start with deterministic merge logic where possible
- use LLM only for ambiguous merge reasoning

Important:
Every update should be logged as a diff:
- previous value
- new value
- reason / evidence

---

## 13. Retrieval Layer
MVP retrieval should prioritize precision and control.

### 13.1 Retrieval Inputs
- selected action
- current state concepts
- interaction pattern
- risk level

### 13.2 Retrieval Targets
- playbooks
- principles
- approved example responses

### 13.3 Retrieval Strategy
Order:
1. filter by tags and applies_when
2. rank by concept overlap
3. optionally re-rank with embedding similarity
4. return top 1 to 3 items

Do not dump many items into generation prompt.

---

## 14. Rule Checker
This is mandatory.

Rule checker should inspect generated response before send.

### Example checks
- no more than one question mark
- no direct confrontation language in high arousal state
- no definitive diagnosis claims
- if risk high, must include escalation wording
- response should not contain too many action options
- response should remain concise

### Implementation
Start with explicit Python rules.
Later add LLM-based critique as second pass.

### Output
- pass/fail
- violated rules
- suggested fix strategy

---

## 15. Generation Layer
Prompt should be built from:
- caregiver message
- current structured state summary
- selected action
- 1 to 3 retrieved playbooks / principles
- explicit instructions for tone and brevity

### Generation goals
- calm
- concise
- action-oriented
- psychologically consistent
- non-intrusive

### Example generation instruction
Write a short response to the caregiver.
Prioritize calming, clarity, and one immediate next step.
Do not diagnose.
Do not ask more than one question.
Do not list many options.

---

## 16. Expert Review Workflow
Need optional review gate.

### Modes
- `manual_review_required`
- `auto_send_low_risk`
- `expert_shadow_mode`

For MVP default:
- all responses require expert review

### Expert actions
- approve
- edit
- reject
- replace
- add note
- propose new rule
- propose new playbook

### UI requirements
Expert should see:
- caregiver message
- current case state summary
- selected action
- retrieved playbooks
- draft response
- rule check results

---

## 17. Admin and Expert UI Requirements
Need minimal but usable interfaces.

### 17.1 Caregiver-facing UI
Minimal for MVP.
Could be:
- basic chat page
- or API endpoints only, if another team handles WhatsApp

### 17.2 Expert UI
Required.
Views:
- inbox of pending drafts
- case detail page
- draft review page
- playbook management page
- rules overview page
- audit trail / logs page

### 17.3 Internal Debug UI
Useful for fast iteration.
Show:
- parser outputs
- state diffs
- selected action
- retrieved playbooks
- rule checker results

---

## 18. Logging and Observability
This is critical for future IP and learning.

Log every turn with:
- raw input message
- parse result
- state before
- state after
- selected action
- retrieved knowledge IDs
- generation prompt version
- draft response
- rule checker outputs
- expert edits
- final sent response

Need searchable logs.

Also store:
- prompt templates version
- model version
- retrieval version
- rule set version

---

## 19. Seed Content to Implement Immediately
Create at least these playbooks:
1. Flashback / high arousal after loud noise
2. Withdrawal and silence after trigger
3. Caregiver over-questioning during acute distress
4. When to call clinician / outside help
5. Boundary setting during irritability

Create at least these principles:
1. Arousal first
2. Reduce cognitive load
3. No confrontation in acute state
4. Follow patient capacity
5. Support presence over content
6. Regulate caregiver first
7. Break escalation loops
8. Offer actionable micro-steps
9. Respect autonomy
10. Escalate only when needed

Create at least these rules:
1. Max one question
2. No diagnosis as fact
3. No confrontation in high arousal
4. Escalation required at specified high-risk condition
5. Keep response concise

---

## 20. Initial Example Data
Seed example patient, caregiver, and interaction from the worked example already defined in project docs.

The seeded scenario should include:
- patient profile with war-related PTSD-like pattern
- caregiver partner with anxiety and repeated questioning tendency
- acute loud-bang crisis message
- expected selected action: `reduce_pressure` or `ground`
- example draft response

Codex should implement seed loaders so the app is usable immediately after install.

---

## 21. Suggested Folder Structure
```text
app/
  api/
  core/
    config.py
    concepts.py
    rules.py
  db/
    models.py
    session.py
    seed.py
  domain/
    schemas/
    services/
      parsing.py
      state_update.py
      action_selection.py
      retrieval.py
      generation.py
      rule_check.py
      expert_review.py
  prompts/
    parse_message.md
    update_state.md
    select_action.md
    generate_response.md
    critique_response.md
  ui/
    templates/ or frontend/
  tests/
```

---

## 22. API Endpoints to Implement
Minimum backend endpoints:

### Caregiver / Messaging
- `POST /threads`
- `POST /threads/{id}/messages`
- `GET /threads/{id}`
- `GET /threads/{id}/messages`

### Drafts / Expert Review
- `GET /expert/drafts/pending`
- `GET /expert/drafts/{id}`
- `POST /expert/drafts/{id}/approve`
- `POST /expert/drafts/{id}/edit`
- `POST /expert/drafts/{id}/reject`

### Playbooks / Principles / Rules
- `GET /playbooks`
- `POST /playbooks`
- `PATCH /playbooks/{id}`
- `GET /principles`
- `GET /rules`

### Debug / Logs
- `GET /debug/interactions/{id}`
- `GET /debug/logs`

---

## 23. Implementation Order
Codex should implement in this order:

### Phase 1: Domain and Storage
- DB models
- seed data
- concept registry
- basic CRUD for messages and playbooks

### Phase 2: Core Services
- parsing service
- state update service
- action selection service
- retrieval service
- generation service
- rule checker

### Phase 3: Orchestration
- end-to-end message pipeline
- draft response creation
- expert review workflow

### Phase 4: UI / Debugging
- expert review pages
- playbook management
- debug inspection pages

### Phase 5: Hardening
- tests
- logging improvements
- prompt versioning
- better error handling

---

## 24. Testing Requirements
At minimum implement:

### Unit tests
- rule checker
- state merge logic
- retrieval ranking
- action selection fallback logic

### Integration tests
- message in → draft out
- rule violation → regeneration or fail
- expert edit flow

### Golden tests
Use seeded worked example and assert:
- parser extracts loud noise trigger
- inferred high arousal
- selected action is appropriate
- generated response remains concise and non-confrontational

---

## 25. Non-Functional Requirements
- code must be clean and modular
- prompt templates separated from business logic
- all main decisions logged
- easy to swap LLM backend
- no secrets hard-coded
- app should run locally with one command after setup

---

## 26. Things Codex Should Avoid
- do not implement giant monolithic prompt chains without structure
- do not over-engineer with full graph DB in MVP
- do not invent hidden domain logic without explicit place in config, prompts, or rules
- do not hard-code many one-off case-specific hacks
- do not store only raw text when structured form is available

---

## 27. Deliverables
Codex should produce:
1. Running local app
2. Seeded example data
3. End-to-end message handling
4. Expert review flow
5. Playbook CRUD
6. Rule checker
7. Tests for core paths
8. README with setup and architecture notes

---

## 28. README Expectations
The generated README should include:
- product purpose
- architecture summary
- setup instructions
- environment variables
- how to seed example data
- how to run backend and frontend
- how to test
- known limitations

---

## 29. Nice-to-Have, Only If Time Allows
- concept registry admin page
- confidence visualization
- state-diff timeline view
- draft comparison view for expert edits
- retrieval explanation panel

---

## 30. Final Instruction to Codex
When implementing, optimize for:
- transparency
- modularity
- fast iteration
- inspectable intermediate states

If a tradeoff exists between a clever shortcut and a clear architecture, choose the clearer architecture.

Do not compress core logic into one opaque chain.
Make each stage visible and debuggable.

