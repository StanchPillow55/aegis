# aegis
Voice-first daily training-decision copilot for functional longevity. Cal Hacks 2026.

## Build philosophy
Agentic loop (Planner/Prompter -> Coder -> Tester -> QA) governed by `success_criteria.yaml`.
Multi-model `llm-council` (`council/council.py`) provides judgment at the Planner & QA gates.
See `CLAUDE.md` for the full build contract.

## Quickstart
1. `cp .env.example .env` and fill keys (Anthropic + Gemini at minimum).
2. `pip install -r requirements.txt`
3. Council sanity check: `python -m council.council "Reply with a one-line plan."`

## Sponsor tracks targeted
Anthropic, Redis, Deepgram, Arize, Sentry, Fetch AI, Band, Simular, Cognition, Browserbase.
