# Existing System Context

Aegis has a FastAPI backend with a Goals API at `/api/goals`. Currently, it uses an in-memory list `_ACTIVE_GOALS` to store goals. If the server is restarted, goals are lost. 
The user has a Kiro task file at `.kiro/specs/aegis-functional-baseline/tasks.md`.

# Proposed Architecture

We will create a standalone utility script `scripts/import_tasks_to_goals.py`. This script will:
1. Open and read `.kiro/specs/aegis-functional-baseline/tasks.md`.
2. Parse lines that match `- [ ] <task>`. We will use a regular expression like `r'^-\s+\[ \]\s+(.*)'` or similar to grab tasks. We can also capture sub-bullets as the `description`.
3. Iterate over the extracted tasks.
4. For each task, send a `POST` request to `http://localhost:8000/api/goals` containing the JSON payload matching the `Goal` model.

# Files / Modules Affected

- `scripts/import_tasks_to_goals.py` (NEW)

# Component Design

- **Parser**: A function `parse_tasks(filepath)` that returns a list of dictionaries `[{"title": "...", "description": "..."}]`.
- **API Client**: A function `import_to_api(tasks, base_url="http://localhost:8000")` that uses Python's standard `urllib.request` to make POST requests, to avoid adding new third-party dependencies if they aren't needed, or `requests`/`httpx` if available. The requirements mention `apscheduler`, `cryptography`, etc. We'll use `urllib.request` for zero-dependency simplicity.

# Data Model

The payload to `POST /api/goals`:
```json
{
  "title": "1. Write bug condition exploration test",
  "description": "...",
  "goal_type": "activity"
}
```

# API / Interface Contracts

We consume the existing `POST /api/goals` endpoint which expects a `Goal` Pydantic model payload.

# Error Handling

If `urllib.error.URLError` is caught (e.g. connection refused), the script prints a helpful message: "Error: Could not connect to Aegis API. Is the server running on http://localhost:8000?".

# Security / Privacy

Local development script, no sensitive data.

# Performance / Scalability

N/A.

# Testing Strategy

- Provide a mock file or simple text block in the script tests to ensure the parser extracts correctly.
- Manual verification: Run the script, then query `GET /api/goals`.

# Requirement Traceability

- REQ-001 -> Parser function using regex.
- REQ-002 -> API Client using `urllib.request`.
- REQ-003 -> JSON mapping logic.
