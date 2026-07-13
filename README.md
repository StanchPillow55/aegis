# aegis (Local-First Open Source)

A daily training-decision copilot for functional longevity. This is the local-first, open-source rewrite of the original Cal Hacks 2026 hackathon project, designed to run completely on your own hardware without requiring paid cloud API keys.

## Quickstart

1. `cp .env.opensource.example .env`
2. Configure models in `.env` (default is `llama3.2` via `ollama`).
3. `pip install -r requirements.txt` (Note: ensure you have playwright browsers installed with `playwright install chromium`)
4. Spin up local Jaeger for tracing: `make os-up`
5. Run the dev server: `make os-dev`
6. Run the smoke demo (in another terminal): `make os-demo`

## Hardware Assumptions
The default runtime is tuned to comfortably run on an **Apple Silicon M2 MacBook Air with 16 GB RAM**.
- **LLM**: `llama3.2` via Ollama (3B params).
- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2`.
- **Memory**: ChromaDB + SQLite.
- **Voice**: `faster-whisper` (STT) + `piper` (TTS).

If you have a stronger machine (e.g. M4 / 32GB+), you can switch models in `.env` (e.g. `qwen2.5:14b` or `llama3:8b`). Run `make os-model-info` for details.

## Testing
Run tests using:
```bash
make os-test
```
Tests include skip guards so that missing models (like `llama3.2` or `faster-whisper`) won't cause the suite to fail.

## Legacy Implementation
The original hackathon implementation (using paid cloud services, proprietary APIs, and sponsor tracks) is preserved in `legacy_hackathon/` for historical reference.
