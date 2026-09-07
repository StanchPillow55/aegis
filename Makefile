.PHONY: os-model-info os-test os-smoke os-demo os-dev os-health mvp-demo

DEV_HOST ?= 127.0.0.1
DEV_PORT ?= 8000

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
	@echo ""
	@echo "=== aegis dev server ==="
	@echo "URL:  http://$(DEV_HOST):$(DEV_PORT)/   (port $(DEV_PORT) is required)"
	@echo "NOTE: 127.0.0.1 means THIS machine only."
	@echo "      If this shell is a Cloud Agent/VM, your laptop browser's 127.0.0.1"
	@echo "      is a different computer and will show ERR_CONNECTION_REFUSED."
	@echo "      Run on your M2 host for local Chrome, or use Tailscale (docs/TAILSCALE.md)."
	@echo "      Override bind: make os-dev DEV_HOST=0.0.0.0"
	@echo "========================"
	@echo ""
	python3 -m uvicorn backend.main:app --host $(DEV_HOST) --port $(DEV_PORT) --reload

os-health:
	@curl -fsS "http://127.0.0.1:$(DEV_PORT)/health" | python3 -m json.tool
	@echo "UI check:"
	@curl -fsS -o /dev/null -w "GET / -> HTTP %{http_code}\n" "http://127.0.0.1:$(DEV_PORT)/"
