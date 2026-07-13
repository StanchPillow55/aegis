# Auth and Setup Bucket List

This table documents everything required to run `aegis` in its new local-first, open-source architecture. Use this as a checklist for your development machine.

| Item Needed | Description / How to Get It | Status |
| :--- | :--- | :--- |
| **Ollama installed** | Native application to run local LLMs. Download from [ollama.com](https://ollama.com). | `Pending` |
| **Default Ollama model pulled** | Run `ollama run llama3.2` to pull the default model used for extraction. | `Pending` |
| **Docker Desktop running** | Required to spin up the local Jaeger instance for tracing. | `Pending` |
| **Chroma local service** | Local vector database. Installed via pip as part of requirements. No separate service needed, uses local directory. | `Ready` |
| **SQLite DB path** | Local relational database for metadata. Automatically created in the project root (`aegis_local.db`). | `Ready` |
| **faster-whisper model** | Local STT. Installed via pip. The model (`tiny.en`) will download automatically on first run. | `Ready` |
| **Piper binary/model** | Local TTS. Download piper and the `en_US-lessac-medium.onnx` model file if testing TTS natively. | `Pending` |
| **Playwright browsers** | Required for scraping WODs. Run `playwright install chromium` after `pip install`. | `Pending` |
| **Jaeger local service** | Distributed tracing backend. Run `make os-up` to spin up via Docker Compose. | `Pending` |
| **Gemini API key (optional)** | Only needed if using cloud fallbacks or AI Studio tools. Add to `.env`. | `Optional` |
| **Legacy sponsor keys (optional)** | Anthropic, Deepgram, Sentry, Redis Cloud keys. Not needed for OS loop, but can be added to `.env` to run legacy code. | `Optional` |
