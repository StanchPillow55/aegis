# CLAUDE.md — aegis build contract (read this first, every session)

## What aegis is
**Daily training-decision copilot for functional longevity**, expanding into a
local-first personal health copilot (wearables, body composition, calendar,
NL/image logging, environment, scoring, goals, alerts, conversational dashboard).

Core loop (preserved):
`Intake → structured health data → evidence → scores → WOD/training context → ONE evidence-bound daily directive`

Canonical scores: **Front-rack, Sleep, Diet, Workout preparation, Overall**.
Current code may still show transitional `readiness`/`soreness` labels — treat as debt.

## Canonical docs
- `docs/PRODUCT_SPEC.md` — product + architecture (single source for “what”)
- `success_criteria.yaml` — Definition of Done (single source for “done”)
- `AGENT_HANDOFF.md` — current state + next implementation slice

## Runtime posture
**Local-first.** LLM inference, storage, normalization, scoring, reasoning: local
(Ollama + SQLite on Apple Silicon M2). Fitbit / Google Calendar / Open-Meteo are
optional external connectors; cache locally; degrade to fixtures/manual entry.
No cloud LLM or cloud DB on the core path. Location is opt-in and never sent to a cloud LLM.

## The accountability contract (NON-NEGOTIABLE)
1. `success_criteria.yaml` is the Definition of Done.
2. NEVER mark a criterion `pass: true` until its verify command passes WITH a linked artifact.
3. Agentic loop: Planner/Prompter → Coder → Tester → QA (fails closed).
4. Status reports must distinguish: UI presence ≠ backend ≠ live integration ≠ E2E verification.
5. Do not implement expanded connectors until schema/provenance/sync docs gates are understood; prefer Slice 0 in AGENT_HANDOFF.

## Repo map
backend/{intake,memory,scorers,agents,reasoner,obs,providers} importer/ frontend/ docs/ tests/ council/ scripts/
