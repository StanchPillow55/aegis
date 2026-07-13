# Agent Handoff

## What was completed
- **Legacy Migration**: Moved all existing sponsor-integrated code into `legacy_hackathon/`. Created `legacy_hackathon/README.md` to explain the history.
- **Provider Interface Layer**: Built open-source, local-first replacements for LLM (Ollama), STT/TTS (faster-whisper, piper), Memory (ChromaDB + SQLite), Browser (Playwright), and Tracing (OpenTelemetry/Jaeger).
- **Core Orchestrator**: Replaced Fetch.ai uAgents with a local Python orchestrator `backend/agents/orchestrator.py`.
- **FastAPI Endpoint**: Exposed the demo loop through a FastAPI app in `backend/main.py`.
- **Success Criteria**: Added local OS metrics (`OS-*`) to `success_criteria.yaml` and marked legacy tracks as `[LEGACY]`.
- **Setup Bucket List**: Created `AUTH_AND_SETUP_BUCKET_LIST.md` containing all setup requirements and dependencies.
- **Docker Compose & Env**: Created `docker-compose.opensource.yml` for Jaeger and `.env.opensource.example`.
- **Makefile**: Updated `Makefile` to include `os-*` targets for the new local-first runtime.
- **Unit Tests**: Wrote tests for local extraction, memory, orchestrator, tracing, and browser. The tests are configured with skip guards or mocked components to pass without the full heavy models loaded.

## What remains blocked
- Running the full live pipeline end-to-end with the heavy local models requires downloading `llama3.2`, `faster-whisper (tiny.en)`, and `piper` models, which should be done by the user on their native machine (Metal acceleration).
- OpenTelemetry tracing visualization requires starting Jaeger.

## Setup Bucket List Needed from User
Please refer to `AUTH_AND_SETUP_BUCKET_LIST.md` for the full list. Highlights:
1. Install and run `ollama` with `ollama run llama3.2`.
2. Run `playwright install chromium` to ensure the local browser can run.
3. Install `docker` and run `make os-up` to spin up Jaeger for tracing.

## Commands to run when back
1. Check model status: `make os-model-info`
2. Start background Jaeger: `make os-up`
3. Run test suite: `make os-test`
4. Start dev server: `make os-dev`
5. Send smoke demo: `make os-demo`

## Success criteria passable
All `OS-*` criteria should now be passable once the models are downloaded by the user, as the architectural scaffolding and tests are fully built.
- `OS-ENV-01`: Backend boots.
- `OS-LLM-01`: Deterministic fallback works.
- `OS-VOICE-01`: Mock works.
- `OS-MEMORY-01`: Local memory logic is in place.
- `OS-ORCH-01`: Orchestrator fully implemented.
- `OS-BROWSER-01`: Local playwright logic in place.
- `OS-OBS-01`: OTel spans implemented.
- `OS-DEMO-01`: Demo endpoint functional.
- `OS-HARDWARE-01`: Docs reflect M2/16GB.

## Known Risks
- Running ChromaDB and Ollama concurrently on 16GB RAM might consume significant resources. `llama3.2` and `tiny.en` were specifically chosen to mitigate this, but if the machine feels sluggish, consider dropping Chroma for pure SQLite.

## Hardware Review
- **M2/16GB**: Expected to be comfortable given the `llama3.2` default which takes ~2-3 GB of RAM.
- **M4/32GB+ (Stretch)**: Can easily upgrade to `qwen2.5:14b` or `llama3:8b` by just changing `OLLAMA_MODEL` in `.env`.
