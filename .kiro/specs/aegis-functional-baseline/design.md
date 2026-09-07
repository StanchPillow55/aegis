# Aegis Functional Baseline Bugfix Design

## Overview

The Aegis application contains 16 defects across three severity tiers (P0–P2) that collectively prevent the server from starting, corrupt runtime state with hardcoded fake data, and silently discard all user-generated data on every restart. This design document describes the targeted fix for each defect group, the formal bug condition and preservation requirements, and the testing strategy that validates each fix without breaking existing behavior.

The fix approach is additive and minimal: no existing public API contracts change, no new frameworks are introduced, and every data store already scaffolded by `init_db()` is used as intended.

---

## Glossary

- **Bug_Condition (C)**: The set of runtime inputs or code paths that trigger defective behavior.
- **Property (P)**: The correct observable outcome that must hold for all inputs in C after the fix.
- **Preservation**: All behaviors outside C that must remain byte-for-byte identical after the fix.
- **F**: The original (unfixed) function or code path.
- **F'**: The fixed function or code path.
- **`user_id`**: The string extracted from the `X-User-ID` HTTP request header, used as the partition key for all per-user SQLite queries.
- **`init_db()`**: The function in `sqlite_store.py` that creates all tables on startup; the `goals`, `safety_thresholds`, and `body_compositions` tables already exist in its schema.
- **`_get_connection()`**: The internal helper in `sqlite_store.py` that returns a `sqlite3.Connection` with WAL mode and row factory set.
- **`get_system_defaults()`**: The function in `anomaly_detector.py` that returns the four hard-coded system safety thresholds.

---

## Bug Details

### Bug Condition

The bugs span 12 distinct failure modes. They are grouped into 12 fix groups below. The unified bug condition is:

```
FUNCTION isBugCondition(call_site)
  INPUT: call_site — any function call or import in the running application
  OUTPUT: boolean

  RETURN (
    -- P0: import-time failures
    call_site.module IN ['apscheduler', 'cryptography', 'google-auth',
                         'google-auth-oauthlib', 'google-api-python-client', 'pytest-mock']
    AND call_site.package NOT IN requirements_txt
  )
  OR (
    call_site.path == 'src/backend/sync/scheduler.py'
    AND NOT file_exists('src/backend/sync/__init__.py')
  )
  OR (
    -- P0: missing user_id argument
    call_site.function IN ['get_log_by_date', 'get_similar_days',
                            'search_similar', 'get_log_by_date']
    AND len(call_site.positional_args) < required_arity(call_site.function)
  )
  OR (
    -- P1: in-memory-only storage
    call_site.storage_target IN ['_ACTIVE_GOALS', '_PENDING_CHECK_INS',
                                  '_ACTIVE_ALERTS', '_MOCK_DB_THRESHOLDS']
    AND NOT call_site.is_backed_by_sqlite
  )
  OR (
    -- P1: hardcoded fake data returned to caller
    call_site.return_value.is_hardcoded == True
    AND call_site.function IN ['build_context', 'get_body_composition',
                                'get_calendar_context', 'compare_periods',
                                'get_correlations', 'get_auth_url',
                                'exchange_code', 'fetch_events',
                                'parse_takeout_zip']
  )
  OR (
    -- P2: test calls wrong endpoint, guardrails corrupt text, Makefile blocks
    call_site IN [wrong_test_endpoint, guardrails_word_replacement, makefile_sync_block]
  )
END FUNCTION
```

### Examples

- **Bug 1.1**: `pip install -r requirements.txt` succeeds but `from apscheduler.schedulers.background import BackgroundScheduler` raises `ModuleNotFoundError` at runtime.
- **Bug 1.3**: `GET /api/directive` returns HTTP 500 with `TypeError: get_log_by_date() missing 1 required positional argument: 'd'`.
- **Bug 1.7**: User creates a goal via `POST /api/goals`, server restarts, `GET /api/goals` returns `[]`.
- **Bug 1.10**: Chat response references "HR 50-160bpm, Resting HR 52bpm" regardless of what Fitbit has synced.
- **Bug 1.15**: LLM says "your HRV is too low" → guardrails rewrites to "your HRV is notable" — grammatically broken.

---

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**

- `POST /api/intake` parsing, scoring, and SQLite persistence remain identical.
- `GET /api/trends` time-series queries from `score_history` remain identical.
- `GET /api/directive` rule-based readiness/soreness/sleep/hydration logic remains identical — only the `user_id` argument threading changes.
- `GET /api/patterns/performance-predictors` and `/insight` continue invoking `day_before_performance()` and `generate_weekly_insight()` without modification.
- `GET /api/goals` response shape (the `Goal` Pydantic model) remains identical.
- `POST /api/goals/{goal_id}/complete` and `confirm-completion` continue updating status and `completed_at`, now also persisting to SQLite.
- `GET /api/settings/thresholds` on a fresh DB continues returning the four system defaults.
- `check_metric_against_thresholds()` continues returning an `Alert` object; `acknowledge_alert()` continues updating acknowledged state.
- `derive_signals()` and `parse_events()` in `google_calendar.py` continue deriving the same signals without modification.
- `query_metric()` tool continues emitting chart specs to `_EMITTED_CHARTS` and returning a confirmation string.
- `apply_guardrails()` called with output containing no prescriptive phrases continues returning the original string unchanged.
- `make test` continues discovering and running all tests under `tests/` with the existing `conftest.py` DB path isolation.

**Scope:**
All inputs that do NOT fall within the bug condition above are completely unaffected by these fixes. This includes all existing API endpoints not listed in the fix groups, all existing Pydantic models, all existing ChromaDB operations, and all existing Fitbit/FitIndex sync flows.

---

## Hypothesized Root Cause

1. **Incomplete `requirements.txt`**: The six missing packages were never added when their importing modules were written. The `sync` package `__init__.py` was omitted, which is required for Python to treat the directory as a package.

2. **Missing `user_id` threading**: The `directive.py`, `patterns.py`, and `logs.py` endpoints were written before `user_id` was added as the first positional argument to the storage functions. The call sites were never updated.

3. **Prototype in-memory lists promoted to production**: `_ACTIVE_GOALS`, `_PENDING_CHECK_INS`, `_ACTIVE_ALERTS`, and `_MOCK_DB_THRESHOLDS` were scaffolded as TODO placeholders. The SQLite tables to back them were created in `init_db()` but the actual read/write wiring was deferred and never completed.

4. **Hardcoded stubs in context and tools**: `context_builder.py` and `tools.py` were written with placeholder strings to unblock UI development. The DB query implementations were never substituted.

5. **Google Calendar mock not replaced**: `get_auth_url()`, `exchange_code()`, and `fetch_events()` were mocked to avoid requiring OAuth credentials in development. The real implementation using `google-auth-oauthlib` was written as comments but never activated.

6. **Takeout parser returns synthetic records**: `parse_takeout_zip()` was written as a proof-of-concept that emits one fake record per heart-rate file. The actual JSON parsing logic for all metric types was never implemented.

7. **Test calls stale endpoint path**: `test_chat.py` was written before the chat history endpoint was moved from `/api/chat/history` to `/api/chat/sessions/{session_id}/history`.

8. **Guardrails uses word substitution instead of sentence rewriting**: `apply_guardrails()` does a regex word replacement (`re.sub(pattern, "notable", ...)`) producing malformed sentences. The goal-aware suppression logic was noted as a TODO but never implemented.

9. **Makefile `dev` target is synchronous**: `backend` runs `uvicorn` in the foreground, so `frontend` never executes. The backgrounding `&` was never added.

---

## Correctness Properties

Property 1: Bug Condition — Application Starts and All Endpoints Respond

_For any_ HTTP request to the Aegis application after `pip install -r requirements.txt`, the server SHALL start without `ModuleNotFoundError` or `ImportError`, and every endpoint listed in the bug report SHALL return a non-500 response when supplied with a valid `X-User-ID` header.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6**

Property 2: Bug Condition — User Data Persists Across Restarts

_For any_ user-created goal, triggered alert, or custom safety threshold, the fixed code SHALL write the record to the appropriate SQLite table immediately and read it back from SQLite on all subsequent requests, so that a server restart returns the same data.

**Validates: Requirements 2.7, 2.8, 2.9**

Property 3: Bug Condition — AI Context Contains Real Data

_For any_ call to `build_context(user_id)` or the four tool stub functions, the fixed code SHALL query the `health_metrics`, `body_compositions`, `calendar_events`, and `goals` SQLite tables and return a formatted string containing values from those tables (or an explicit "no data" message if the tables are empty).

**Validates: Requirements 2.10, 2.11**

Property 4: Bug Condition — Google Calendar OAuth Produces Real Tokens

_For any_ call to `get_auth_url()` with a valid `redirect_uri`, the fixed function SHALL return a URL that begins with `https://accounts.google.com/o/oauth2/auth` and contains real `client_id`, `scope`, and `redirect_uri` parameters constructed from the configured credentials.

**Validates: Requirements 2.12**

Property 5: Bug Condition — Takeout Parser Reads Actual Zip Payload

_For any_ valid Google Health Takeout zip containing at least one supported metric file, the fixed `parse_takeout_zip()` SHALL return records whose `value` fields are parsed from the actual `fpVal` entries in the JSON, not from a hardcoded constant.

**Validates: Requirements 2.13**

Property 6: Bug Condition — Test Suite Passes on Correct Endpoints

_For any_ run of `make test`, `test_chat.py` SHALL call `GET /api/chat/sessions/{session_id}/history` with a valid `session_id` and receive a 200 response containing the messages from that session.

**Validates: Requirements 2.14**

Property 7: Bug Condition — Guardrails Rewrites Produce Grammatical Sentences

_For any_ LLM response containing a prescriptive phrase, the fixed `apply_guardrails()` SHALL replace the phrase with a neutral, grammatically correct rewrite (e.g. "your HRV is below your recent baseline") rather than a bare word substitution.

**Validates: Requirements 2.15**

Property 8: Bug Condition — `make dev` Starts Both Services

_For any_ execution of `make dev`, the `uvicorn` process SHALL be backgrounded with `&` so that the `npm run dev` frontend target also executes in the same shell session.

**Validates: Requirements 2.16**

Property 9: Preservation — Existing Intake and Trend Flows Unchanged

_For any_ input that does NOT involve the bug condition (i.e., normal intake submissions, trend queries, directive requests with correct call signatures), the fixed code SHALL produce the same result as the original code, preserving all existing scoring, persistence, and response-shaping logic.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10, 3.11, 3.12**

---

## Fix Implementation

### Fix Group 1 — Missing Dependencies + Package Structure (Bugs 1.1, 1.2)

**File: `requirements.txt`**

Append the six missing packages with pinned or minimum-bound versions:

```
apscheduler==3.10.4
cryptography>=42.0.0
google-auth>=2.29.0
google-auth-oauthlib>=1.2.0
google-api-python-client>=2.130.0
pytest-mock>=3.14.0
```

**File: `src/backend/sync/__init__.py`**

Create as a new file containing only a module docstring:
```python
"""Sync scheduler package."""
```

No logic required — presence of the file is sufficient for Python's import system to resolve `src.backend.sync.scheduler`.

---

### Fix Group 2 — API TypeError Fixes (Bugs 1.3–1.6)

**Pattern applied to three files:**

Import `Header` from `fastapi` and add `x_user_id: str = Header(default="default_user")` to the relevant route handler signature. Derive `user_id = x_user_id` and thread it through all downstream storage calls.

**`src/backend/api/directive.py`**

- Add `x_user_id: str = Header(default="default_user")` to `todays_directive()`.
- Change `get_log_by_date(date.today())` → `get_log_by_date(user_id, date.today())`.
- Change `get_similar_days(today_log, n=3)` → `get_similar_days(user_id, today_log, n=3)`.

**`src/backend/api/patterns.py`**

- Add `x_user_id: str = Header(default="default_user")` to `semantic_search()`.
- Change `search_similar(query, n=n)` → `search_similar(user_id, query, n=n)`.

**`src/backend/api/logs.py`**

- The `GET /api/logs` route already has `x_user_id: str = Header(...)` wired correctly via `get_logs_range`.
- The `GET /api/logs/{log_date}` route handler `get_log()` calls `get_log_by_date(d)` without `user_id`. Add `x_user_id: str = Header(default="default_user")` and change to `get_log_by_date(user_id, d)`.

---

### Fix Group 3 — Goal Persistence (Bug 1.7)

**`src/backend/intelligence/goal_tracker.py`**

Remove `_ACTIVE_GOALS` and `_PENDING_CHECK_INS` module-level lists. Replace every read/write with direct SQLite queries using `_get_connection()`.

New function signatures and their SQL:

```python
def get_active_goals(user_id: str) -> List[Goal]:
    # SELECT * FROM goals WHERE user_id=? AND status='active'

def save_goal(goal: Goal, user_id: str) -> None:
    # INSERT OR REPLACE INTO goals (id, user_id, title, ...) VALUES (?, ?, ?, ...)

def update_goal_progress(goal_id: str, progress_pct: float, current_value: float) -> None:
    # UPDATE goals SET progress_pct=?, current_value=? WHERE id=?

def create_pending_check_in(check_in: GoalCheckIn, user_id: str) -> None:
    # INSERT INTO goal_check_ins (id, goal_id, timestamp, source, message, requires_confirmation)

def get_pending_check_ins(user_id: str) -> List[GoalCheckIn]:
    # SELECT gc.* FROM goal_check_ins gc
    # JOIN goals g ON gc.goal_id = g.id
    # WHERE g.user_id=? AND gc.requires_confirmation=1
```

`check_goals_against_metrics()` must accept `user_id` and use `get_active_goals(user_id)` plus `update_goal_progress()` and `create_pending_check_in()`.

**`src/backend/api/goals.py`**

Replace all direct references to `_ACTIVE_GOALS` and `_PENDING_CHECK_INS` with calls to the rewritten `goal_tracker` functions, threading `user_id` from the `X-User-ID` header (add `x_user_id: str = Header(default="default_user")` to each route handler that does not yet have it).

---

### Fix Group 4 — Alert Persistence (Bug 1.8)

**`src/backend/storage/sqlite_store.py` — `init_db()`**

Add a `safety_alerts` table migration inside the existing `executescript`:

```sql
CREATE TABLE IF NOT EXISTS safety_alerts (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    metric_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    current_value REAL,
    threshold_value REAL,
    timestamp TEXT NOT NULL,
    acknowledged INTEGER NOT NULL DEFAULT 0
);
```

**`src/backend/safety/anomaly_detector.py`**

Remove `_ACTIVE_ALERTS`. Replace with three SQLite-backed functions:

```python
def save_alert(alert: Alert, user_id: str) -> None:
    # INSERT OR REPLACE INTO safety_alerts ...

def get_active_alerts(user_id: str) -> List[Alert]:
    # SELECT * FROM safety_alerts WHERE user_id=? AND acknowledged=0

def acknowledge_alert(alert_id: str, user_id: str) -> bool:
    # UPDATE safety_alerts SET acknowledged=1 WHERE id=? AND user_id=?
```

`check_metric_against_thresholds()` gains a `user_id` parameter and calls `save_alert(alert, user_id)` instead of `_ACTIVE_ALERTS.append(alert)`.

**`src/backend/api/alerts.py`**

Add `x_user_id: str = Header(default="default_user")` to both route handlers. Pass `user_id` to `get_active_alerts(user_id)` and `acknowledge_alert(alert_id, user_id)`.

---

### Fix Group 5 — Threshold Persistence (Bug 1.9)

**`src/backend/api/settings.py`**

Remove `_MOCK_DB_THRESHOLDS`. The `safety_thresholds` table already exists from `init_db()`.

Add a seeding helper called at the top of `list_thresholds()`:

```python
def _seed_defaults_if_empty(conn):
    count = conn.execute("SELECT COUNT(*) FROM safety_thresholds WHERE is_system_default=1").fetchone()[0]
    if count == 0:
        for t in get_system_defaults():
            conn.execute("INSERT OR IGNORE INTO safety_thresholds (...) VALUES (...)", (...))
```

Route handler rewrites:

```python
def list_thresholds(x_user_id: str = Header(default="default_user")):
    # _seed_defaults_if_empty(conn)
    # SELECT * FROM safety_thresholds WHERE is_system_default=1 OR user_id=?

def create_threshold(threshold: SafetyThreshold, x_user_id: str = Header(default="default_user")):
    # INSERT INTO safety_thresholds ...

def delete_threshold(threshold_id: str, x_user_id: str = Header(default="default_user")):
    # DELETE FROM safety_thresholds WHERE id=? AND (user_id=? OR is_system_default=0)
```

---

### Fix Group 6 — Context Builder Real Data (Bug 1.10)

**`src/backend/intelligence/context_builder.py`**

Change the signature of `build_context()` to `build_context(user_id: str) -> str`.

Replace the three hardcoded strings with live queries:

**Vitals (last 24h):**
```python
cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
rows = conn.execute(
    "SELECT metric_type, value, unit, timestamp FROM health_metrics "
    "WHERE user_id=? AND timestamp >= ? ORDER BY timestamp DESC",
    (user_id, cutoff)
).fetchall()
```
Group rows by `metric_type`; compute `min/max` for `heart_rate`, `latest` for `resting_heart_rate`, `hrv`, `spo2`. Fall back to `"No vitals data synced in the last 24h."` if empty.

**Body composition (most recent record):**
```python
row = conn.execute(
    "SELECT * FROM body_compositions ORDER BY date DESC LIMIT 1"
).fetchone()
```
Fall back to `"No body composition data recorded."` if `None`.

**Calendar (today's events):**
```python
rows = conn.execute(
    "SELECT * FROM calendar_events WHERE date(start_time) = date('now') ORDER BY start_time"
).fetchall()
```
Count events; scan `derived_signals` JSON for `travel`. Fall back to `"No calendar data synced."` if empty.

**`src/backend/api/chat.py`**

Change `context = build_context()` to `context = build_context(x_user_id)` in `generate_response()`. The `x_user_id` value is already available in that scope.

---

### Fix Group 7 — LLM Tools Real Data (Bug 1.11)

**`src/backend/intelligence/tools.py`**

Add `user_id` as the first parameter to the four stub functions and implement real DB queries:

**`get_body_composition(user_id, date_range)`:**
Parse `date_range` string ("last 30 days", "this month") into a `start_date`. Query `body_compositions` for that range. Return a formatted string: `"N measurements. Latest: W lbs, F% body fat (DATE). 30-day change: ΔW lbs, ΔF% body fat."` or `"No body composition data for this period."`.

**`get_calendar_context(user_id, date_range)`:**
Parse date range, query `calendar_events`. Return formatted count, travel days, early/late event flags.

**`compare_periods(user_id, metric, period_a, period_b)`:**
Query `health_metrics` for `metric_type=metric` in both periods. Compute averages. Return `"[Metric] avg X in period_a vs Y in period_b (Z%)."`.

**`get_correlations(user_id, metric_a, metric_b, days)`:**
Query both metrics from `health_metrics` over `days` days. Align by day (inner join on `date(timestamp)`). Compute Pearson correlation coefficient. Return `"[metric_a] and [metric_b] show [strength] [direction] correlation (r=R) over N days."`.

The caller in `api/chat.py` already carries `x_user_id` in context; pass it through when constructing tool call arguments.

---

### Fix Group 8 — Google Calendar Real OAuth (Bug 1.12)

**`src/backend/config.py`**

Add two new optional fields to `Settings`:
```python
google_client_id: str | None = None
google_client_secret: str | None = None
```

**`.env.example`** (create if absent)

Add:
```
# GOOGLE_CLIENT_ID=
# GOOGLE_CLIENT_SECRET=
```

**`src/backend/importers/google_calendar.py`**

Replace the three mock functions:

**`get_auth_url(redirect_uri)`:**
```python
settings = get_settings()
flow = Flow.from_client_config(
    {"web": {
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }},
    scopes=SCOPES,
    redirect_uri=redirect_uri
)
auth_url, _ = flow.authorization_url(access_type="offline", include_granted_scopes="true")
return auth_url
```
Return `None` if `google_client_id` or `google_client_secret` is not configured.

**`exchange_code(code, redirect_uri)`:**
```python
flow.fetch_token(code=code)
creds = flow.credentials
return {
    "access_token": creds.token,
    "refresh_token": creds.refresh_token,
    "expires_in": int((creds.expiry - datetime.now()).total_seconds())
}
```

**`fetch_events(credentials_dict, start_time, end_time)`:**
Uncomment the real implementation already present in the file:
```python
creds = Credentials(**credentials_dict)
service = build("calendar", "v3", credentials=creds)
events_result = service.events().list(
    calendarId="primary",
    timeMin=start_time.isoformat(),
    timeMax=end_time.isoformat(),
    singleEvents=True,
    orderBy="startTime"
).execute()
return events_result.get("items", [])
```

---

### Fix Group 9 — Takeout Real Parsing (Bug 1.13)

**`src/backend/importers/takeout.py`**

Replace the body of `parse_takeout_zip()` with a real parser that handles all supported metric types.

Google Health Takeout JSON structure:
```json
{
  "Data Points": [
    {
      "fitValue": [{"value": {"fpVal": 72.0}}],
      "startTimeNanos": "1705123200000000000",
      "endTimeNanos":   "1705123260000000000"
    }
  ]
}
```

File pattern → metric type mapping:
| Filename pattern | `MetricType` | Value extraction |
|---|---|---|
| `*heart_rate*` | `heart_rate` | `fitValue[0].value.fpVal` |
| `*step_count*` | `steps` | `fitValue[0].value.fpVal` |
| `*heart_rate_variability*` or `*hrv*` | `hrv` | `fitValue[0].value.fpVal` |
| `*calories*` | `calories` | `fitValue[0].value.fpVal` |
| `*sleep_segment*` | `sleep_duration` | `(endTimeNanos - startTimeNanos) / 1e9 / 60` (minutes) |

Timestamp: `datetime.fromtimestamp(int(startTimeNanos) / 1e9, tz=timezone.utc).isoformat()`

For each `Data Points` entry that successfully parses, append a dict `{"metric": ..., "value": ..., "timestamp": ...}` to `results`. Wrap each point in a `try/except` and log parse errors rather than aborting the entire import.

---

### Fix Group 10 — Test Endpoint Fix (Bug 1.14)

**`tests/test_chat.py`**

The test currently calls `GET /api/chat/history`. Replace with the correct pattern:

1. Use the `session_id` returned in the `POST /api/chat` response body.
2. Call `GET /api/chat/sessions/{session_id}/history` with the `X-User-ID` header.
3. Assert the response is 200 and contains the two expected messages.

The test must also use `client.post("/api/chat", data={...}, headers={"X-User-ID": "test_user"})` since the chat endpoint uses `Form(...)`, not JSON body.

---

### Fix Group 11 — Guardrails Goal-Aware Rewriting (Bug 1.15)

**`src/backend/safety/guardrails.py`**

Replace the word-substitution approach with a sentence-level rewrite map. Process the response sentence by sentence to preserve surrounding context.

Rewrite map:
```python
REWRITES = [
    (r"(?i)\byou should\s+(\w[\w\s]*?)(?=[.,;!?]|$)", r"\1 may be worth considering"),
    (r"(?i)\byou need to\s+(\w[\w\s]*?)(?=[.,;!?]|$)", r"\1 may be worth considering"),
    (r"(?i)\btoo high\b", "above your recent baseline"),
    (r"(?i)\btoo low\b", "below your recent baseline"),
    (r"(?i)\bconcerning\b", "notable compared to your baseline"),
    (r"(?i)\bdangerous\b", "outside the typical range"),
]
```

Goal-aware suppression: if `active_goal_metrics` contains a metric that can be inferred from the sentence context, skip the rewrite for that sentence (normative framing is appropriate when a user has set an explicit goal for that metric).

Implementation sketch:
```python
def apply_guardrails(llm_response: str, active_goal_metrics: List[MetricType] = None) -> str:
    if active_goal_metrics is None:
        active_goal_metrics = []
    goal_metric_names = {m.value.lower() for m in active_goal_metrics}
    
    sentences = re.split(r'(?<=[.!?])\s+', llm_response)
    result = []
    for sentence in sentences:
        sentence_lower = sentence.lower()
        # Skip rewriting if sentence mentions a metric with an active goal
        has_active_goal_metric = any(name in sentence_lower for name in goal_metric_names)
        if has_active_goal_metric:
            result.append(sentence)
            continue
        rewritten = sentence
        for pattern, replacement in REWRITES:
            rewritten = re.sub(pattern, replacement, rewritten)
        result.append(rewritten)
    return " ".join(result)
```

---

### Fix Group 12 — Makefile dev Target (Bug 1.16)

**`Makefile`**

Change the `backend` target to background `uvicorn` with `&`, and update `dev` to call both targets:

```makefile
dev:
	uvicorn src.backend.main:app --reload --host 0.0.0.0 --port 8000 &
	cd src/frontend && npm run dev
```

The `backend` and `frontend` phony targets can remain for individual use; only the `dev` target body needs the `&`.

---

## Testing Strategy

### Validation Approach

Testing follows a two-phase approach for each fix group: first, confirm the bug manifests on the unfixed code (counterexample phase), then verify the fix corrects the behavior and that all preserved behaviors remain intact.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate each defect BEFORE implementing the fix.

**Test Cases (run on unfixed code):**

1. **Import test**: `python -c "import src.backend.sync.scheduler"` → raises `ModuleNotFoundError` for `apscheduler` and `ImportError` for missing `__init__.py`.
2. **Directive endpoint test**: `GET /api/directive` with `X-User-ID` header → HTTP 500, `TypeError` in traceback.
3. **Goal restart test**: Create goal via `POST /api/goals`, restart server (re-import app), `GET /api/goals` → empty list.
4. **Context builder test**: Call `build_context()` → returns literal string `"HR 50-160bpm, Resting HR 52bpm"` regardless of DB contents.
5. **Guardrails test**: `apply_guardrails("your HRV is too low")` → returns `"your HRV is notable"` (malformed).
6. **Takeout test**: Upload zip with real heart-rate data → all returned records have `value == 65.0`.
7. **Test suite test**: `make test` → `test_chat.py` fails with 404 on `GET /api/chat/history`.

**Expected counterexamples:**
- Import failures, TypeError stack traces, empty goal lists, hardcoded strings in context, malformed guardrails output, fake takeout values, and a failing test for the wrong endpoint path.

### Fix Checking

**Goal**: After each fix, verify the property holds for all inputs in C.

```
FOR ALL call_site WHERE isBugCondition(call_site) DO
  result := fixed_code(call_site)
  ASSERT property(result)
END FOR
```

Key assertions per group:
- **Group 1**: `pip install -r requirements.txt` exits 0; `from src.backend.sync.scheduler import ...` succeeds.
- **Group 2**: All four endpoints return non-500 with `X-User-ID` header present.
- **Group 3**: Goal created, server reimported (or new `TestClient`), goal still retrievable.
- **Group 4**: Alert triggered, server reimported, alert still in active list.
- **Group 5**: Custom threshold created, server reimported, threshold visible; system defaults present on empty DB.
- **Group 6**: `build_context(user_id)` with real metric rows returns actual values, not hardcoded strings.
- **Group 7**: Tool functions with real DB rows return non-placeholder strings containing actual numbers.
- **Group 8**: `get_auth_url("http://localhost/callback")` returns URL starting with `https://accounts.google.com/o/oauth2/auth` when credentials are configured.
- **Group 9**: Zip containing real `{"Data Points": [...fpVal: 72.0...]}` → returned records have `value == 72.0`.
- **Group 10**: `test_chat.py` passes; history endpoint returns 200 with correct messages.
- **Group 11**: `apply_guardrails("your HRV is too low")` → `"your HRV is below your recent baseline"` (grammatical).
- **Group 12**: `make dev` spawns both `uvicorn` and `npm run dev` processes.

### Preservation Checking

**Goal**: Verify that all inputs outside the bug condition produce identical results before and after the fix.

```
FOR ALL call_site WHERE NOT isBugCondition(call_site) DO
  ASSERT original_behavior(call_site) == fixed_behavior(call_site)
END FOR
```

**Testing approach**: Property-based tests generate diverse inputs across the existing intake, trend, and directive flows to confirm no regressions. The `conftest.py` DB isolation ensures tests do not share state.

**Preservation test cases:**
1. `POST /api/intake` with valid payload → same scoring, same SQLite row shape, same response.
2. `GET /api/trends` with date range → same score time-series from `score_history`.
3. `GET /api/directive` with user data → same rule-based directive text, different only in that `user_id` is now correctly threaded.
4. `GET /api/settings/thresholds` on fresh DB → four system defaults returned (seeded on first call).
5. `apply_guardrails("Your readiness looks good.")` → unchanged string returned.
6. `derive_signals([event])` with early-morning event → `early_morning: True` signal still derived.

### Unit Tests

- Test `apply_guardrails()` with each prescriptive pattern and verify grammatical rewrites.
- Test `apply_guardrails()` with a sentence containing a metric in `active_goal_metrics` — verify no rewrite.
- Test `apply_guardrails()` with neutral text — verify no change (preservation).
- Test `parse_takeout_zip()` with a synthetic zip containing known `fpVal` values — verify exact parsed values.
- Test `parse_takeout_zip()` with sleep segment entries — verify duration calculation in minutes.
- Test `build_context(user_id)` with empty DB — verify fallback strings, no crash.
- Test `build_context(user_id)` with seeded metrics rows — verify actual values appear in output.
- Test goal create → `save_goal()` → `get_active_goals()` round-trip via SQLite.
- Test alert trigger → `save_alert()` → `get_active_alerts()` → `acknowledge_alert()` round-trip.

### Property-Based Tests

- Generate random `llm_response` strings with zero prescriptive phrases; assert `apply_guardrails()` returns them unchanged (preservation, Property 9).
- Generate random `llm_response` strings containing any of the six prescriptive patterns; assert no occurrence of the original pattern remains in the output (fix, Property 7).
- Generate random `Goal` objects, save them, retrieve them, assert field equality (round-trip correctness, Property 2).
- Generate random `Alert` objects with `user_id`, save them, retrieve with correct `user_id`, assert non-empty; retrieve with different `user_id`, assert empty (user isolation).

### Integration Tests

- Full startup smoke test: import `app`, call `GET /health`, assert `{"status": "ok"}`.
- Goal lifecycle: create → list → complete → list again (status filter); restart client, list again → same result.
- Alert lifecycle: trigger via `check_metric_against_thresholds()` → list alerts → acknowledge → list again (empty).
- Chat context: seed a `health_metrics` row, call `POST /api/chat`, verify LLM was called with a context string containing real metric values (not hardcoded).
- Threshold seeding: fresh DB → `GET /api/settings/thresholds` → 4 results; create custom → `GET` → 5 results; restart client → still 5 results.
