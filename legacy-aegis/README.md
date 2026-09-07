# aegis
Voice-first daily training-decision copilot for functional longevity. Cal Hacks 2026.

## Build philosophy
Agentic loop (Planner/Prompter -> Coder -> Tester -> QA) governed by `success_criteria.yaml`.
Multi-model `llm-council` (`council/council.py`) provides judgment at the Planner & QA gates.
See `CLAUDE.md` for the full build contract.

## Local-First Architecture Goals
Ollama, SQLite/Chroma, and OpenTelemetry are planned targets unless otherwise explicitly implemented as cloud services.

## Quickstart
1. `cp .env.example .env` (Add API keys if using cloud fallbacks)
2. `pip install -r requirements.txt`
3. Council sanity check: `python -m council.council "Reply with a one-line plan."`
