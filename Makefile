.PHONY: os-model-info os-test os-smoke

os-model-info:
	@echo "Local model info:"
	@echo "  default_model: not selected in foundation branch"
	@echo "  hardware_target: Apple Silicon M2, 16 GB RAM"
	@echo "  status: foundation validation only"

os-test:
	python -m compileall backend importer tests scripts
	python scripts/check_file_sanity.py
	python scripts/validate_success_criteria.py
	python -m pytest tests/ -q

os-smoke:
	python -m pytest tests/test_health.py -q
