# CLAUDE.md — aegis build contract (read this first, every session)

## What aegis is
**Daily training-decision copilot for functional longevity**, expanding into a
local-first personal health copilot and a **living evidence-backed Goal Graph**.

Core loop (preserved):
`Intake → structured health data → evidence → goal-relevant signals → WOD/training context → ONE evidence-bound daily directive` (+ HITL goal/task suggestions)

**Front-rack, Sleep, Diet, Workout preparation** remain analyzers / pluggable signals —
not permanent hardcoded dashboard categories. Overall score is optional.
Current code may still show transitional `readiness`/`soreness` labels — treat as debt.

## Canonical docs
- `docs/PRODUCT_SPEC.md` — product + architecture (single source for “what”)
- `docs/GOAL_GRAPH.md` — Goal Graph + context-aware planning layer
- `docs/IMPLEMENTATION_PLAN.md` — ordered slices (GL0–GL6 + S*)
- `success_criteria.yaml` — Definition of Done (single source for “done”)
- `docs/SC_MATURITY.md` — verified vs fixture vs planned
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
5. Goal Graph is incomplete without journal → evidence → suggestion → human approval → dashboard update.
6. Never silently mutate goals/tasks.

## Repo map
backend/{intake,memory,scorers,signals,agents,reasoner,obs,providers,goals,chat} importer/ frontend/ docs/ tests/ council/ scripts/
