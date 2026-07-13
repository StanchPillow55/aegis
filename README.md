# aegis
Voice-first daily training-decision copilot for functional longevity. Cal Hacks 2026.

## Build philosophy
Agentic loop (Planner/Prompter -> Coder -> Tester -> QA) governed by `success_criteria.yaml`.
Multi-model `llm-council` (`council/council.py`) provides judgment at the Planner & QA gates.
See `CLAUDE.md` for the full build contract.

## Open Source Migration Setup
This project is migrating to a fully local open-source runtime environment. 

- **M2/16 GB Default Path**: Default local environment target.
- **M4 Stretch Path**: Extended capabilities for M4 devices.
- **Required Local Installs**: 
  - Check `AUTH_AND_SETUP_BUCKET_LIST.md` for missing installations (Docker, Ollama, Playwright, Jaeger, Whisper, Piper, etc.)
- **Optional Cloud Fallbacks**: Cloud APIs remain available if local runs fail.
- **Legacy Sponsor Mode**: Maintained for Hackathon compatibility.

## Quickstart
1. `cp .env.example .env` and fill keys (Anthropic + Gemini at minimum).
2. `pip install -r requirements.txt`
3. Council sanity check: `python -m council.council "Reply with a one-line plan."`

## Sponsor tracks targeted
Anthropic, Redis, Deepgram, Arize, Sentry, Fetch AI, Band, Simular, Cognition, Browserbase.
