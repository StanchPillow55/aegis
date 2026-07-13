# Auth and Setup Bucket List

This table documents everything required to run `aegis` in its new local-first, open-source architecture. Use this as a checklist for your development machine.

| Item Needed | Required/Optional | Why it is needed | Install / Auth Command / Link | Environment Variable | How to test it | Current Status |
|-------------|------------------|------------------|-------------------------------|----------------------|----------------|----------------|
| **Ollama** | Required | Local LLM runtime | [Install Ollama](https://ollama.com) | `OLLAMA_BASE_URL` | `ollama --version` | NEEDED |
| **llama3.2** | Required | Default LLM for extraction / synthesis (M2/16GB) | `ollama run llama3.2` | `OLLAMA_MODEL` | `ollama list` | NEEDED |
| **qwen2.5 / llama3** | Optional | Alternative local models (M4/32GB+) | `ollama run qwen2.5:14b` | `OLLAMA_MODEL` | `ollama list` | OPTIONAL |
| **Docker Desktop** | Required | To run Jaeger for OpenTelemetry traces | [Install Docker](https://docs.docker.com/desktop/) | N/A | `docker --version` | NEEDED |
| **Jaeger Container** | Required | OpenTelemetry tracing UI and Collector | `make os-up` | `OTEL_EXPORTER_OTLP_ENDPOINT` | Go to `http://localhost:16686` | NEEDED |
| **faster-whisper** | Required | Local STT (Voice to Text) | Python dependency (installed via requirements.txt) | `FASTER_WHISPER_MODEL` | Included in Python tests | NEEDED |
| **piper-tts** | Required | Local TTS (Text to Voice) | [Install Piper](https://github.com/rhasspy/piper) and download model to project root | `PIPER_MODEL_PATH` | `./piper --help` | NEEDED |
| **Playwright Browsers**| Required | Local headless browser for WOD importer | `playwright install chromium` | N/A | `playwright --version` | NEEDED |
| **Gemini API Key** | Optional | Optional Cloud fallback | [Get Key](https://aistudio.google.com/) | `GEMINI_API_KEY` | Use curl to fallback endpoints | OPTIONAL |
| **Legacy Anthropic** | Optional | To run legacy code | N/A | `ANTHROPIC_API_KEY` | N/A | SKIPPED |
| **Legacy Deepgram** | Optional | To run legacy code | N/A | `DEEPGRAM_API_KEY` | N/A | SKIPPED |
| **Legacy Sentry** | Optional | To run legacy code | N/A | `SENTRY_DSN` | N/A | SKIPPED |
| **Legacy Browserbase**| Optional | To run legacy code | N/A | `BROWSERBASE_API_KEY`| N/A | SKIPPED |
| **Legacy Redis URL** | Optional | To run legacy code | N/A | `REDIS_URL` | N/A | SKIPPED |
| **Legacy Fetch/Band** | Optional | To run legacy code | N/A | N/A | N/A | SKIPPED |
