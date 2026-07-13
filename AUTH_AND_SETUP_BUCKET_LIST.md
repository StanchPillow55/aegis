# Auth and Setup Bucket List

| Item | Required/Optional | Why | Install/Auth Command | Env Var | Test Command | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Ollama | Required | Local LLM hosting | `brew install ollama` | None | `ollama --version` | Pending |
| llama3.2 | Required | Default extraction | `ollama run llama3.2` | `OLLAMA_MODEL=llama3.2` | `ollama run llama3.2 "hello"` | Pending |
| Docker | Required | Tracing (Jaeger) | Install Docker Desktop | None | `docker --version` | Pending |
| Playwright | Required | Web scraping | `playwright install chromium` | None | `playwright --version` | Pending |
| Whisper | Required | Local STT | `pip install faster-whisper` | None | `python -c "import faster_whisper"` | Pending |
| Piper | Optional | Local TTS | `brew install piper` | None | `piper --version` | Pending |
| Jaeger | Required | OpenTelemetry | `make os-up` | None | `curl localhost:16686` | Pending |
| Anthropic | Optional | Cloud fallback | Add key to env | `ANTHROPIC_API_KEY` | None | Pending |
