# Overview

The user wants a mechanism to extract the implementation tasks defined in `.kiro/specs/aegis-functional-baseline/tasks.md` and add them as goals to the Aegis Goals API.

# Goals

- Create a script that parses `.kiro/specs/aegis-functional-baseline/tasks.md`.
- Extract each task (e.g., "- [ ] 1. Write bug condition exploration test") and any relevant sub-bullet details.
- Send a POST request for each extracted task to the Goals API to create a `Goal` entity.
- The `Goal` should have `goal_type = 'activity'` and `status = 'active'`.

# Non-Goals

- Do not implement a permanent, recurring sync. This is a one-off import utility.
- Do not modify the existing Goals API to support bulk import; use the existing `POST /api/goals` endpoint.
- Do not migrate the in-memory `_ACTIVE_GOALS` store to SQLite; this script only needs to work against the current running process state.

# Functional Requirements

- **REQ-001**: The script SHALL parse the specified markdown file and correctly identify top-level tasks.
- **REQ-002**: The script SHALL hit the `POST /api/goals` endpoint on `http://localhost:8000` (configurable via environment variable or argument, defaulting to localhost:8000).
- **REQ-003**: The script SHALL map task descriptions to the `title` and `description` fields of the Goal model.

# Acceptance Criteria

- **REQ-001**: Running the parsing function on the markdown file yields exactly the 8 main tasks listed (or the exact number of top-level tasks).
- **REQ-002**: Executing the script against a running local Aegis server results in the goals being populated and visible via `GET /api/goals`.
- **REQ-003**: The created goals have the correct title and the correct `goal_type` ("activity").

# Edge Cases

- The local server is not running: the script should gracefully fail and tell the user to start the server.
- The markdown format changes: the script should rely on standard `^[ \t]*- \[ \]\s*` bullet points.

# Constraints

- Script should be a standalone Python script located in `scripts/`.
- Must use standard library `urllib` or `requests`/`httpx` if already in `requirements.txt`. (Will use `httpx` or `requests` depending on what's available, or `urllib.request` to avoid dependencies).

# Open Questions

- None. This is a straightforward utility script.
