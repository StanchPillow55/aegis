.PHONY: os-up os-down os-test os-dev os-smoke os-demo os-model-info

os-up:
	docker-compose -f docker-compose.opensource.yml up -d

os-down:
	docker-compose -f docker-compose.opensource.yml down

os-test:
	pytest tests/ -q

os-dev:
	uvicorn backend.main:app --reload --port 8000

os-smoke:
	curl -s http://localhost:8000/health

os-demo:
	curl -X POST http://localhost:8000/demo -H "Content-Type: application/json" -d '{"transcript":"I slept 8 hours and my lower back is sore. I had chicken and rice for lunch."}'

os-model-info:
	@echo "=== Local Model Info ==="
	@echo "Default Model: llama3.2 (runs comfortably on M2 / 16GB)"
	@echo "Stretch Alternatives (M4/32GB+): qwen2.5:14b, llama3:8b, mistral:7b"
	@echo "STT: faster-whisper (tiny.en by default)"
	@echo "TTS: piper-tts (en_US-lessac-medium.onnx)"
	@echo "Embeddings: sentence-transformers/all-MiniLM-L6-v2"
	@echo "Checking if models are available (mocked output if missing):"
	@echo "OLLAMA_MODEL=$(OLLAMA_MODEL)"
	@echo "======================="
