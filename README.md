# aegis

**Daily training-decision copilot for functional longevity** — expanding into a **local-first personal health copilot** (wearables, body composition, calendar/lifestyle context, natural-language + image logging, environmental context, health scoring, goals, alerts, conversational dashboard).

Still centered on one evidence-bound daily training directive:

`Intake → structured health data → evidence → scores → WOD/training context → directive`

## Docs (read in order)
1. [`docs/PRODUCT_SPEC.md`](docs/PRODUCT_SPEC.md) — canonical product + architecture spec  
2. [`success_criteria.yaml`](success_criteria.yaml) — Definition of Done  
3. [`AGENT_HANDOFF.md`](AGENT_HANDOFF.md) — current state + next slice  
4. [`CLAUDE.md`](CLAUDE.md) — build contract  

## What works in this repository now
- FastAPI app: `/health`, `/api/intake`, `/api/directive`, `/api/logs/recent`
- Text intake → structured fields → **transitional** scores (`readiness` / `sleep` / `soreness` / `diet`) → directive
- SQLite memory with basic retrieval (dedup / provenance incomplete)
- Optional Ollama; heuristic fallback when Ollama is down
- Simple text-first UI with Today / History / Conflicts + disclaimer
- Slice 0: provenance, SQLite durability, evidence dedup, today-wins conflicts
- OS foundation + Slice 0 gates green; **23** automated tests

**Not in this tree yet** (specified, not implemented): Fitbit, FITINDEX, Calendar, chat/vision, LLM metric tools, charts, alerts, goals, sync registry, PWA/Tailscale, canonical Front-rack / Workout-prep / Overall scores.

## Quickstart (Apple Silicon M2 or Linux)
```bash
cp .env.example .env
python3 -m pip install -r requirements.txt
make os-test
make os-demo
make os-dev   # http://127.0.0.1:8000
```

Optional: `ollama pull llama3.2`

## Local-first boundary
LLM, storage, scoring, and reasoning are local. Fitbit / Google Calendar / Open-Meteo are optional external connectors whose data is cached locally. The app must remain usable with fixtures and manual entry when those services are unavailable. No cloud LLM or cloud database is required.

## Build philosophy
Agentic loop governed by `success_criteria.yaml`. See `CLAUDE.md`.
