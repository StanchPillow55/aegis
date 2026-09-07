#!/bin/bash
exec > qa_results.txt 2>&1

for PR in 14 13 15; do
  echo "======================================"
  echo "========== PR $PR checks =========="
  echo "======================================"
  gh pr view $PR --json number,title,baseRefName,headRefName,commits,statusCheckRollup,mergeStateStatus
  echo "--- diff name-only ---"
  gh pr diff $PR --name-only
  echo "--- diff patch ---"
  gh pr diff $PR --patch
  echo "--- checks ---"
  gh pr checks $PR || true
  
  if [ "$PR" -eq 14 ]; then
    BRANCH="feat/os-provider-interfaces"
    FILE="backend/providers/llm.py"
  elif [ "$PR" -eq 13 ]; then
    BRANCH="feat/os-local-llm"
    FILE="backend/local_llm.py"
  else
    BRANCH="feat/os-docs"
    FILE="README.md"
  fi
  
  git checkout $BRANCH
  echo "--- file sanity ---"
  python -m compileall backend importer tests scripts
  python scripts/check_file_sanity.py
  python scripts/validate_success_criteria.py
  python -m pytest tests/ -q || true
  make os-test || true
  
  echo "--- remote file verification ---"
  gh api --method GET "repos/StanchPillow55/aegis/contents/$FILE" -f ref="$BRANCH" --jq .content | base64 -d | head -n 120
done
