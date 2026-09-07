# Implementation Tasks

- [x] **T001 — Create parser for tasks.md**
  - Requirements: REQ-001
  - Depends on: none
  - Files/areas: `scripts/import_tasks_to_goals.py`
  - Objective: Write a function `parse_tasks(filepath)` that extracts tasks and their sub-items into a structured format.
  - Implementation notes: Use regex to match `- [ ]`.
  - Validation: Add a small `if __name__ == "__main__":` block that prints the parsed tasks to stdout to verify extraction works on `.kiro/specs/aegis-functional-baseline/tasks.md`.

- [x] **T002 — Implement API client and main loop**
  - Requirements: REQ-002, REQ-003
  - Depends on: T001
  - Files/areas: `scripts/import_tasks_to_goals.py`
  - Objective: Write a function `send_to_api(tasks)` that sends each task to `POST /api/goals`.
  - Implementation notes: Use `urllib.request`. Handle ConnectionRefused errors gracefully.
  - Validation: Run the script while the FastAPI server is running, and verify the goals appear by checking the server output or visiting the `GET /api/goals` endpoint in a browser.

### Traceability

| Requirement | Design Section | Task(s) | Validation |
| ----------- | -------------- | ------- | ---------- |
| REQ-001     | Component Design | T001  | Manual log check |
| REQ-002     | Error Handling   | T002  | API request check |
| REQ-003     | Data Model       | T002  | API request check |
