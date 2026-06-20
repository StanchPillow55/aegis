.PHONY: dev test

dev:
	uvicorn backend.main:app --reload

test:
	pytest -q
