# Agent Handoff Document

## Current Status

- OS migration foundation has been merged into `master`.
- Provider skeletons have been added.
- Local LLM fallback now returns an IntakeResult-compatible dictionary shape.
- Redis workflow trigger has been narrowed so OS migration branches should not be blocked by Redis checks.

## Validation Status

Current blocker:
- `make os-test` failed because `success_criteria.yaml` did not parse with `criteria` as a list.

Required before next wave:
- `python scripts/validate_success_criteria.py` must pass.
- `make os-test` must pass.

## Next Recommended Branches

Only start these after `make os-test` passes on `master`:

- `feat/os-memory`: SQLite/Chroma local memory.
- `feat/os-voice`: faster-whisper and Piper skeletons.
- `feat/os-tracing`: OpenTelemetry and Jaeger skeleton.

## Rules

- Do not mark success criteria `pass: true` unless the verify command passed and the artifact field is non-null.
- Missing local services should become skip guards and bucket-list entries, not hard failures.
