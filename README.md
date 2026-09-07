# aegis
Voice-capable daily training-decision copilot for functional longevity — **local-first / open-source**.

Text UI is primary. Browser dictation and spoken TTS are opt-in. No paid cloud APIs required.

## What works now
- FastAPI app with `/health`, `/api/intake`, `/api/directive`, `/api/logs/recent`
- Local intake extraction via **Ollama** when running, else a deterministic heuristic
- SQLite memory with hashing-vector retrieval (no Redis Cloud)
- Deterministic readiness / sleep / soreness / diet scorers → one daily directive
- OpenTelemetry-style local span scaffold (console exporter)
- Optional STT/TTS adapters (faster-whisper / Piper / pyttsx3) behind feature flags
- Text-first frontend at `/`

## Quickstart (Apple Silicon M2 or Linux)
```bash
cp .env.example .env
python3 -m pip install -r requirements.txt
make os-test
make os-demo
make os-dev   # http://127.0.0.1:8000
```

### Optional local LLM
```bash
# Install Ollama, then:
ollama pull llama3.2
```

### Optional voice
Set `VOICE_STT_ENABLED=true` / `VOICE_TTS_ENABLED=true` in `.env` and install
`faster-whisper` and/or `pyttsx3` (or a Piper model path). The UI also supports
browser dictation and browser `speechSynthesis` without those packages.

## Build philosophy
Agentic loop governed by `success_criteria.yaml`. See `CLAUDE.md`.

## Future notes
Linux/CI is supported for foundation tests. Kubernetes + MoE serving is a later
scaling track — not required for local foundation readiness.
