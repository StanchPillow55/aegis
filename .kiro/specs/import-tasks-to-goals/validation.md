# Validation Plan

## Layer 1 — Static Validation
- Run standard linter/formatter on `scripts/import_tasks_to_goals.py`.

## Layer 2 — Automated Tests
- N/A for a one-off script, but we will test the parser function directly.

## Layer 3 — Acceptance Validation

| Requirement | Acceptance Criterion | Validation Method | Result |
| ----------- | -------------------- | ----------------- | ------ |
| REQ-001     | Script parses top-level tasks | Inspection / Dry run | PENDING |
| REQ-002     | Script hits POST /api/goals | Execution against server | PENDING |
| REQ-003     | Created goals have correct payload | GET /api/goals check | PENDING |

## Layer 4 — Integration / Runtime Validation
- Start the FastAPI server using `python -m src.backend.main` (or whatever the standard start command is).
- Run `python scripts/import_tasks_to_goals.py`.
- Ensure it completes successfully.
- Terminate the server.

## Layer 5 — Regression Validation
- N/A (this is a standalone script that doesn't modify the existing application code).
