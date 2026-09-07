# CLAUDE.md — aegis build contract (read this first, every session)

## What aegis is
Local-first AI copilot for functional longevity. User submits a daily
training/recovery/nutrition update (text primary; optional voice dictation);
aegis emits ONE evidence-bound daily training directive. Spoken TTS is opt-in.

## Runtime posture (current)
**Open-source / local-only.** Do not require Anthropic, Gemini, Redis Cloud,
Deepgram, Sentry, Browserbase, Fetch/Band, or other paid APIs for core paths.
Preferred stack:
- LLM: Ollama (`llama3.2` default on M2/16GB) + heuristic fallback
- Memory: SQLite (hashing-vector retrieval); Chroma optional later
- Voice: faster-whisper / Piper or browser APIs (optional)
- Obs: local OpenTelemetry-style spans (console); no Sentry required
- UI: text-first frontend served by FastAPI

Legacy hackathon cloud modules may remain in-tree but must not block local boot.

## The accountability contract (NON-NEGOTIABLE)
1. `success_criteria.yaml` is the single source of truth ("Definition of Done").
2. NEVER mark a module complete until its SC rows are `pass: true` WITH a linked artifact.
3. Use the agentic loop: Planner/Prompter -> Coder -> Tester -> QA/Validation.
4. External calls emit local spans via `backend.providers.tracing`.

## Cost discipline
Default to local models. If cloud keys appear in `.env`, treat them as optional
dev overrides only — never as required settings.

## Repo map
backend/{intake,memory,scorers,agents,reasoner,obs,providers} importer/ frontend/ tests/ council/ scripts/
