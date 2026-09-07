#!/bin/bash
exec > qa_workflow_results.txt 2>&1

echo "======================================"
echo "========== Workflow Fix Check =========="
echo "======================================"
echo "--- git log ---"
git log -1 -p

echo "--- file sanity ---"
python -m compileall backend importer tests scripts
python scripts/check_file_sanity.py
python scripts/validate_success_criteria.py
python -m pytest tests/ -q || true
make os-test || true

echo "--- remote file verification (on master) ---"
gh api --method GET "repos/StanchPillow55/aegis/contents/.github/workflows/redis-test.yml" -f ref="master" --jq .content | base64 -d
