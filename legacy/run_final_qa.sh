#!/bin/bash
exec > qa_final_results.txt 2>&1

echo "======================================"
echo "========== Final QA Checks =========="
echo "======================================"

echo "--- git log (last 5 commits on master) ---"
git log -5 --stat

echo "--- test execution ---"
make os-test || true

echo "--- file sanity ---"
python -m compileall backend importer tests scripts
python scripts/check_file_sanity.py
python scripts/validate_success_criteria.py

echo "--- File Verification: Provider LLM ---"
cat backend/providers/llm.py
echo "--- File Verification: Local LLM Fallback ---"
cat backend/local_llm.py
echo "--- File Verification: Local LLM Tests ---"
cat tests/test_local_llm.py
echo "--- File Verification: AGENT_HANDOFF.md ---"
cat AGENT_HANDOFF.md
