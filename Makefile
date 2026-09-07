.PHONY: os-model-info os-test os-smoke os-demo os-dev mvp-demo

os-model-info:
	@echo "Local model info:"
	@echo "  default_model: llama3.2 (Ollama)"
	@echo "  alternatives: qwen2.5:14b, mistral:7b"
	@echo "  hardware_target: Apple Silicon M2, 16 GB RAM"
	@echo "  fallback: deterministic heuristic extractor (no network)"
	@echo "  status: open-source foundation"

os-test:
	python3 -m compileall backend importer tests scripts
	python3 scripts/check_file_sanity.py
	python3 scripts/validate_success_criteria.py
	python3 -m pytest tests/ -q

os-smoke:
	python3 -m pytest tests/test_health.py -q

os-demo:
	python3 scripts/os_demo.py

mvp-demo:
	python3 scripts/mvp_demo.py

os-dev:
	python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
