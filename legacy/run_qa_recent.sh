#!/bin/bash
exec > qa_results_recent.txt 2>&1

for PR in 16 13 15; do
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
  
  if [ "$PR" -eq 16 ]; then
    BRANCH="master"
    FILE="backend/providers/llm.py"
  elif [ "$PR" -eq 13 ]; then
    BRANCH="master"
    FILE="backend/local_llm.py"
  else
    BRANCH="master"
    FILE="README.md"
  fi
  
  echo "--- remote file verification (on master) ---"
  gh api --method GET "repos/StanchPillow55/aegis/contents/$FILE" -f ref="master" --jq .content | base64 -d | head -n 120
done

echo "=== file sanity (on master) ==="
git checkout master
git pull origin master
python -m compileall backend importer tests scripts
python scripts/check_file_sanity.py
python scripts/validate_success_criteria.py
python -m pytest tests/ -q || true
make os-test || true

