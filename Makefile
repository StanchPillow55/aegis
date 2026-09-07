.PHONY: dev test backend frontend install setup ollama-check

# ─── Setup ────────────────────────────────────────────────────────────
setup: install ollama-check
	@echo "✓ Setup complete. Run 'make dev' to start."

install:
	pip install -r requirements.txt
	cd src/frontend && npm install

ollama-check:
	@which ollama > /dev/null 2>&1 || (echo "⚠ Ollama not installed. Get it at https://ollama.ai" && exit 0)
	@ollama list 2>/dev/null | grep -q "llama3.2" || echo "⚠ Run: ollama pull llama3.2"
	@ollama list 2>/dev/null | grep -q "llava" || echo "⚠ Run: ollama pull llava"

# ─── Development ──────────────────────────────────────────────────────
dev:
	uvicorn src.backend.main:app --reload --host 0.0.0.0 --port 8000 &
	cd src/frontend && npm run dev

backend:
	uvicorn src.backend.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd src/frontend && npm run dev

# ─── Testing ──────────────────────────────────────────────────────────
test:
	python -m pytest tests/ -v

test-quick:
	python -m pytest tests/ -q --tb=short

# ─── Data ─────────────────────────────────────────────────────────────
reset-db:
	rm -rf data/aegis.db data/chroma
	@echo "✓ Database reset"
