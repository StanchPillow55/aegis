#!/bin/bash
echo "=== Check bases ==="
gh pr view 14 --json number,baseRefName,headRefName,mergeStateStatus,statusCheckRollup || true
gh pr view 13 --json number,baseRefName,headRefName,mergeStateStatus,statusCheckRollup || true
gh pr view 15 --json number,baseRefName,headRefName,mergeStateStatus,statusCheckRollup || true

echo "=== Verify remote contents ==="
for spec in \
  "feat/os-provider-interfaces:backend/providers/llm.py" \
  "feat/os-provider-interfaces:tests/test_provider_interfaces.py" \
  "feat/os-local-llm:backend/local_llm.py" \
  "feat/os-local-llm:tests/test_local_llm.py" \
  "feat/os-docs:AUTH_AND_SETUP_BUCKET_LIST.md" \
  "feat/os-docs:success_criteria.yaml"
do
  branch="${spec%%:*}"
  path="${spec#*:}"
  echo "===== $branch :: $path ====="
  gh api --method GET \
    "repos/StanchPillow55/aegis/contents/$path" \
    -f ref="$branch" \
    --jq .content | base64 -d | sed -n '1,160p'
done
