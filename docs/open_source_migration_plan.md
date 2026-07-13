# Open Source Migration Plan

## Current Privileged Dependency Inventory
- **Anthropic**: Extraction and Directive Synthesis.
- **Deepgram**: Speech-to-Text and Text-to-Speech.
- **Redis Cloud**: Vector Database and Cache.
- **Sentry**: Distributed Tracing.
- **Browserbase / Stagehand**: Cloud Browser Automation.
- **Fetch AI**: Agent Orchestration.
- **Arize / Phoenix**: ML observability.
- **Band**: Agent Messaging Bus.
- **Cognition**: Build Tooling.
- **Simular**: Demo automation.

## Open Source Replacement Stack
- **Backend Framework**: FastAPI + Pydantic
- **Local LLM Runtime**: Ollama (via `httpx` HTTP API)
- **Local STT**: `faster-whisper`
- **Local TTS**: `piper-tts`
- **Memory**: SQLite (for structured logs/cache) + ChromaDB (for vector search)
- **Embeddings**: `sentence-transformers` (`all-MiniLM-L6-v2`)
- **Browser Automation**: Local `playwright`
- **Observability**: OpenTelemetry + Jaeger
- **Orchestration**: Python-based typed orchestrator logic inside FastAPI

## Hardware Assumptions
- **Default Baseline**: M2 Apple Silicon with 16 GB RAM.
- **Stretch Target**: M4 Apple Silicon with 32+ GB RAM.

## Default Local Model Choice
- **LLM (Ollama)**: `llama3.2`
  - *Why*: At 3B parameters, it runs extremely fast on a 16 GB M2 Mac and uses very little RAM, leaving room for ChromaDB and other background services. It supports JSON mode well for extraction.
- **STT**: `faster-whisper` (`tiny.en`)
  - *Why*: It's exceptionally small and fast, perfect for a minimum spanning demo that doesn't eat up the remaining 16 GB RAM overhead.

## Alternative Model Choices
For stronger hardware (e.g. M4 / 32 GB):
- **LLM**: `llama3:8b` or `qwen2.5:14b` for richer and more nuanced extraction and synthesis.
- **STT**: `faster-whisper` (`base.en` or `small.en`) for higher accuracy transcription.

## Risks
- Running ChromaDB, Ollama, and STT/TTS in memory concurrently on an M2/16GB machine could cause swap usage. The defaults (llama3.2 + tiny.en) mitigate this risk.
- Local LLMs may struggle with precise schema extraction compared to Claude Sonnet. Fallback logic is provided for tests.

## Rollback Plan
- The legacy sponsor-integrated implementation is perfectly preserved in `legacy_hackathon/`.
- To rollback, run `git revert` or simply restore from `legacy_hackathon/`.

## Implementation Order
1. Move legacy codebase to `legacy_hackathon/`.
2. Scaffold new open-source root structure.
3. Build new Provider Interface Layer (`llm`, `speech`, `memory`, `browser`, `tracing`).
4. Re-implement core pipeline in `backend/agents/orchestrator.py` and `backend/main.py`.
5. Write setup docs (`AUTH_AND_SETUP_BUCKET_LIST.md`).
6. Add unit tests with mock fallbacks for local models.
