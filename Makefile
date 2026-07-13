.PHONY: os-model-info os-test os-smoke

os-model-info:
	@echo "Local Model Info: Using foundational models placeholder"

os-test:
	pytest tests/ -q

os-smoke:
	@echo "Smoke test placeholder. Ensure os-dev is running if using curl."
	python -c "import httpx; print(httpx.get('http://127.0.0.1:8000/health').json())" || echo "TestClient handles this in CI for now"
