# Implementation Plan: aegis-functional-baseline

## Overview

This task list implements the fixes for 16 defects (P0–P2) that prevent the Aegis application from starting, cause API endpoints to crash with TypeErrors, silently discard all user data on restart by using in-memory lists instead of SQLite, return hardcoded fake data to the AI context, and break dev tooling. The tasks follow the exploratory bugfix workflow: write tests against unfixed code first, then implement each fix, then verify.

## Tasks

- [ ] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Application Crashes on Import and Endpoints Return 500
  - **CRITICAL**: This test MUST FAIL on unfixed code — failure confirms the bugs exist
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior — it will validate the fixes when it passes after implementation
  - **GOAL**: Surface counterexamples demonstrating the import failures and TypeError crashes
  - **Scoped PBT Approach**: Scope to the concrete failing cases — import of `src.backend.main`, `GET /api/directive`, `GET /api/patterns/search?query=test`, `GET /api/logs/2024-01-01` each with `X-User-ID: test_user`
  - Test that importing `src.backend.main` raises `ModuleNotFoundError` (apscheduler absent from requirements.txt)
  - Test that `from src.backend.sync.scheduler import start_scheduler` raises `ImportError` (missing `__init__.py`)
  - Test that `GET /api/directive` with `X-User-ID` header returns HTTP 500 with `TypeError` in detail
  - Test that `GET /api/patterns/search?query=test` with `X-User-ID` header returns HTTP 500
  - Test that `GET /api/logs/2024-01-01` with `X-User-ID` header returns HTTP 500
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests FAIL (this is correct — it proves the P0 bugs exist)
  - Document counterexamples found: `ModuleNotFoundError: No module named 'google.oauth2'` prevents all endpoints from loading.
  - [x] Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Existing Intake, Trends, and Scoring Flows Unchanged
  - **IMPORTANT**: Follow observation-first methodology
  - Observe: `POST /api/intake` with valid payload on unfixed code (non-buggy path) returns 200 with scoring data
  - Observe: `GET /api/trends` with valid date range returns score time-series rows
  - Observe: `apply_guardrails("Your readiness looks good.")` returns the original string unchanged
  - Observe: `derive_signals([event])` with an early-morning event returns `early_morning: True` signal
  - Write property-based test: for all valid intake payloads, `POST /api/intake` response shape and scoring logic are unchanged
  - Write property-based test: for all neutral LLM responses (zero prescriptive phrases), `apply_guardrails()` returns input unchanged
  - Verify tests PASS on UNFIXED code (these code paths are not in the bug condition)
  - **EXPECTED OUTCOME**: Tests PASS (confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.9, 3.11_

- [x] 3. Fix P0 — Missing dependencies and sync package init

  - [x] 3.1 Add missing packages to requirements.txt
    - Append to `requirements.txt`:
      ```
      apscheduler==3.10.4
      cryptography>=42.0.0
      google-auth>=2.29.0
      google-auth-oauthlib>=1.2.0
      google-api-python-client>=2.130.0
      pytest-mock>=3.14.0
      ```
    - Run `pip install -r requirements.txt` and verify exit code 0
    - _Bug_Condition: `package NOT IN requirements_txt` for the six missing libraries_
    - _Expected_Behavior: `pip install -r requirements.txt` exits 0; all six packages importable_
    - _Preservation: all existing pinned packages in requirements.txt remain unchanged_
    - _Requirements: 2.1_

  - [x] 3.2 Create `src/backend/sync/__init__.py`
    - Create new file `src/backend/sync/__init__.py` containing only:
      ```python
      """Sync scheduler package."""
      ```
    - Verify `from src.backend.sync.scheduler import start_scheduler` imports without error
    - _Bug_Condition: `src/backend/sync/__init__.py` does not exist_
    - _Expected_Behavior: sync directory is a valid Python package; scheduler imports succeed_
    - _Preservation: no existing sync logic is modified_
    - _Requirements: 2.2_

  - [x] 3.3 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Application Starts and All Endpoints Respond
    - **IMPORTANT**: Re-run the SAME test from task 1 — do NOT write a new test
    - Run `python -c "import src.backend.main"` — assert no ModuleNotFoundError
    - Run `python -c "from src.backend.sync.scheduler import start_scheduler"` — assert no ImportError
    - **EXPECTED OUTCOME**: Import tests PASS (confirms P0 import bugs are fixed)
    - _Requirements: 2.1, 2.2_

  - [x] 3.4 Verify preservation tests still pass
    - **Property 2: Preservation** - Existing Intake and Trends Flows Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions from dependency additions)

- [x] 4. Fix P0 — TypeError in directive, patterns, and logs endpoints

  - [x] 4.1 Fix `src/backend/api/directive.py`
    - Add `from fastapi import Header` to imports
    - Add `x_user_id: str = Header(default="default_user")` to `todays_directive()` signature
    - Change `get_log_by_date(date.today())` → `get_log_by_date(x_user_id, date.today())`
    - Change `get_similar_days(today_log, n=3)` → `get_similar_days(x_user_id, today_log, n=3)`
    - _Bug_Condition: `get_log_by_date(date.today())` called without `user_id`_
    - _Expected_Behavior: endpoint extracts `user_id` from `X-User-ID` header and threads it correctly_
    - _Preservation: rule-based directive text generation logic unchanged_
    - _Requirements: 2.3, 2.4, 3.3_

  - [x] 4.2 Fix `src/backend/api/patterns.py`
    - Add `from fastapi import Header` to imports
    - Add `x_user_id: str = Header(default="default_user")` to `semantic_search()` signature
    - Change `search_similar(query, n=n)` → `search_similar(x_user_id, query, n=n)`
    - _Bug_Condition: `search_similar(query, n=n)` called without `user_id`_
    - _Expected_Behavior: endpoint passes `user_id` as first argument to `search_similar`_
    - _Preservation: `performance_predictors` and `weekly_insight` routes unchanged_
    - _Requirements: 2.5, 3.4_

  - [x] 4.3 Fix `src/backend/api/logs.py`
    - Add `x_user_id: str = Header(default="default_user")` to `get_log()` handler signature
    - Change `get_log_by_date(d)` → `get_log_by_date(x_user_id, d)` in `get_log()`
    - (The `list_logs` handler already has `x_user_id` wired correctly — do not modify it)
    - _Bug_Condition: `get_log_by_date(d)` called without `user_id` in `GET /api/logs/{log_date}`_
    - _Expected_Behavior: `get_log()` extracts user ID from header and passes it to storage_
    - _Preservation: `list_logs` handler and `get_logs_range` call unchanged_
    - _Requirements: 2.6_

  - [x] 4.4 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Endpoints Return Non-500 With X-User-ID Header
    - **IMPORTANT**: Re-run the SAME test from task 1 — do NOT write a new test
    - Using a TestClient: `GET /api/directive`, `GET /api/patterns/search?query=test`, `GET /api/logs/2024-01-01` all return non-500 with `X-User-ID: test_user`
    - **EXPECTED OUTCOME**: All three endpoint tests PASS
    - _Requirements: 2.3, 2.4, 2.5, 2.6_

  - [x] 4.5 Verify preservation tests still pass
    - **Property 2: Preservation** - Existing Intake and Trends Flows Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)

- [x] 5. Fix P1 — Persist goals to SQLite

  - [x] 5.1 Rewrite `src/backend/intelligence/goal_tracker.py`
    - Remove `_ACTIVE_GOALS` and `_PENDING_CHECK_INS` module-level lists
    - Import `_get_connection` from `src.backend.storage.sqlite_store`
    - Implement `get_active_goals(user_id: str) -> List[Goal]`:
      `SELECT * FROM goals WHERE user_id=? AND status='active'`
    - Implement `save_goal(goal: Goal, user_id: str) -> None`:
      `INSERT OR REPLACE INTO goals (id, user_id, title, description, goal_type, metric_type, target_value, current_value, direction, unit, timeframe_start, timeframe_end, status, created_at, completed_at, completion_confirmed_by, progress_pct, success_criteria, notes) VALUES (...)`
    - Implement `update_goal_progress(goal_id: str, progress_pct: float, current_value: float) -> None`:
      `UPDATE goals SET progress_pct=?, current_value=? WHERE id=?`
    - Implement `create_pending_check_in(check_in: GoalCheckIn, user_id: str) -> None`:
      `INSERT INTO goal_check_ins (id, goal_id, timestamp, source, message, requires_confirmation) VALUES (...)`
    - Implement `get_pending_check_ins(user_id: str) -> List[GoalCheckIn]`:
      `SELECT gc.* FROM goal_check_ins gc JOIN goals g ON gc.goal_id = g.id WHERE g.user_id=? AND gc.requires_confirmation=1`
    - Update `check_goals_against_metrics(metrics, user_id: str)` to call `get_active_goals(user_id)`, `update_goal_progress()`, and `create_pending_check_in(check_in, user_id)`
    - Update `suggest_goal_from_conversation()` to call `save_goal(goal, user_id)` — add `user_id` parameter
    - _Bug_Condition: `_ACTIVE_GOALS` and `_PENDING_CHECK_INS` used as storage; not backed by SQLite_
    - _Expected_Behavior: all goal reads/writes go through SQLite `goals` and `goal_check_ins` tables_
    - _Preservation: `GoalStatus`, `GoalType`, `GoalDirection`, `GoalCheckIn` models unchanged_
    - _Requirements: 2.7, 3.5, 3.6_

  - [x] 5.2 Rewrite `src/backend/api/goals.py`
    - Remove `from src.backend.intelligence.goal_tracker import _ACTIVE_GOALS, _PENDING_CHECK_INS`
    - Import `get_active_goals, save_goal, get_pending_check_ins, update_goal_progress` from `goal_tracker`
    - Add `from fastapi import Header` to imports
    - Add `x_user_id: str = Header(default="default_user")` to all route handlers
    - `list_goals`: replace list comprehension with `get_active_goals(user_id)` (filtered by status if provided)
    - `create_goal`: call `save_goal(goal, user_id)` instead of `_ACTIVE_GOALS.append(goal)`
    - `complete_goal_manually`: query goal from SQLite by id, update status, call `save_goal(goal, user_id)`
    - `get_pending_confirmations`: replace `_PENDING_CHECK_INS` with `get_pending_check_ins(user_id)`
    - `confirm_ai_completion`: update goal in SQLite, remove check-in from `goal_check_ins` table
    - `reject_ai_completion`: delete check-in from `goal_check_ins` table
    - _Bug_Condition: direct `_ACTIVE_GOALS` list manipulation in route handlers_
    - _Expected_Behavior: all route handlers thread `user_id` through goal_tracker SQLite functions_
    - _Requirements: 2.7, 3.5, 3.6_

  - [x] 5.3 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - User Data Persists Across Restarts
    - **IMPORTANT**: Re-run the SAME test from task 1 — do NOT write a new test
    - Create goal via `POST /api/goals` with `X-User-ID: test_user`
    - Create a NEW `TestClient(app)` instance (simulates server restart — no shared in-memory state)
    - `GET /api/goals` with `X-User-ID: test_user` → assert the created goal is returned
    - **EXPECTED OUTCOME**: Goal persists across client re-creation (confirms SQLite persistence)
    - _Requirements: 2.7_

  - [x] 5.4 Verify preservation tests still pass
    - **Property 2: Preservation** - Existing Goal Response Shape Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - Assert `GET /api/goals` response shape matches the `Goal` Pydantic model
    - **EXPECTED OUTCOME**: Tests PASS (no regressions in goal API contract)

- [x] 6. Fix P1 — Persist safety alerts to SQLite

  - [x] 6.1 Add `safety_alerts` table to `src/backend/storage/sqlite_store.py`
    - Inside the existing `init_db()` executescript, add:
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
    - _Bug_Condition: `safety_alerts` table does not exist; alerts stored only in `_ACTIVE_ALERTS`_
    - _Expected_Behavior: `init_db()` creates `safety_alerts` table on startup_
    - _Preservation: all other tables in `init_db()` executescript unchanged_
    - _Requirements: 2.8_

  - [x] 6.2 Rewrite `src/backend/safety/anomaly_detector.py`
    - Remove `_ACTIVE_ALERTS` module-level list
    - Import `_get_connection` from `src.backend.storage.sqlite_store`
    - Implement `save_alert(alert: Alert, user_id: str) -> None`:
      `INSERT OR REPLACE INTO safety_alerts (id, user_id, metric_type, severity, message, current_value, threshold_value, timestamp, acknowledged) VALUES (...)`
    - Implement `get_active_alerts(user_id: str) -> List[Alert]`:
      `SELECT * FROM safety_alerts WHERE user_id=? AND acknowledged=0`
    - Implement `acknowledge_alert(alert_id: str, user_id: str) -> bool`:
      `UPDATE safety_alerts SET acknowledged=1 WHERE id=? AND user_id=?`; return `rowcount > 0`
    - Add `user_id: str` parameter to `check_metric_against_thresholds()`; call `save_alert(alert, user_id)` instead of `_ACTIVE_ALERTS.append(alert)`
    - Keep `get_system_defaults()` completely unchanged
    - _Bug_Condition: `_ACTIVE_ALERTS` used as storage; `check_metric_against_thresholds` has no `user_id`_
    - _Expected_Behavior: alerts written to `safety_alerts` table and scoped by `user_id`_
    - _Preservation: `check_metric_against_thresholds` threshold evaluation logic unchanged; `get_system_defaults()` unchanged_
    - _Requirements: 2.8, 3.7, 3.8_

  - [x] 6.3 Fix `src/backend/api/alerts.py`
    - Add `from fastapi import Header` to imports
    - Add `x_user_id: str = Header(default="default_user")` to `list_active_alerts()` and `ack_alert()`
    - Change `get_active_alerts()` → `get_active_alerts(x_user_id)`
    - Change `acknowledge_alert(alert_id)` → `acknowledge_alert(alert_id, x_user_id)`
    - _Bug_Condition: alert functions called without `user_id`; no user isolation_
    - _Expected_Behavior: alerts are user-scoped; different `user_id` sees empty alert list_
    - _Requirements: 2.8, 3.8_

  - [x] 6.4 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - User Data Persists Across Restarts
    - **IMPORTANT**: Re-run the SAME test from task 1 — do NOT write a new test
    - Trigger alert via `check_metric_against_thresholds(metric, thresholds, user_id="test_user")`
    - Create new `TestClient(app)` instance
    - `GET /api/alerts` with `X-User-ID: test_user` → assert alert is returned
    - Acknowledge alert → `GET /api/alerts` → assert empty list
    - `GET /api/alerts` with `X-User-ID: other_user` → assert empty list (user isolation)
    - **EXPECTED OUTCOME**: Tests PASS (confirms alert persistence and isolation)
    - _Requirements: 2.8_

  - [x] 6.5 Verify preservation tests still pass
    - **Property 2: Preservation** - Alert Return Type and Ack Logic Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - **EXPECTED OUTCOME**: Tests PASS (no regressions)

- [x] 7. Fix P1 — Persist safety thresholds to SQLite

  - [x] 7.1 Rewrite `src/backend/api/settings.py`
    - Remove `_MOCK_DB_THRESHOLDS` module-level list
    - Add `from fastapi import Header` and `from src.backend.storage.sqlite_store import _get_connection`
    - Add seeding helper:
      ```python
      def _seed_defaults_if_empty(conn):
          count = conn.execute("SELECT COUNT(*) FROM safety_thresholds WHERE is_system_default=1").fetchone()[0]
          if count == 0:
              for t in get_system_defaults():
                  conn.execute(
                      "INSERT OR IGNORE INTO safety_thresholds (id, metric_type, condition, value, window_hours, severity, message, is_system_default, user_modified) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      (t.id, t.metric_type.value, t.condition.value, t.value, t.window_hours, t.severity.value, t.message, 1, 0)
                  )
              conn.commit()
      ```
    - Rewrite `list_thresholds(x_user_id: str = Header(default="default_user"))`:
      Call `_seed_defaults_if_empty(conn)`; query `SELECT * FROM safety_thresholds WHERE is_system_default=1 OR user_id=?`
    - Rewrite `create_threshold(threshold, x_user_id: str = Header(default="default_user"))`:
      `INSERT INTO safety_thresholds (..., user_id, is_system_default, user_modified) VALUES (..., ?, 0, 1)`
    - Rewrite `delete_threshold(threshold_id, x_user_id: str = Header(default="default_user"))`:
      `DELETE FROM safety_thresholds WHERE id=? AND (user_id=? OR is_system_default=0)`
    - _Bug_Condition: `_MOCK_DB_THRESHOLDS` in-memory list used; thresholds discarded on restart_
    - _Expected_Behavior: thresholds read/written from `safety_thresholds` SQLite table; defaults seeded on first call_
    - _Preservation: system defaults (`get_system_defaults()`) unchanged; fresh DB always returns 4 defaults_
    - _Requirements: 2.9, 3.7_

  - [x] 7.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - User Data Persists Across Restarts
    - **IMPORTANT**: Re-run the SAME test from task 1 — do NOT write a new test
    - Fresh DB → `GET /api/settings/thresholds` → assert 4 system defaults returned
    - `POST /api/settings/thresholds` to create custom threshold
    - Create new `TestClient(app)` instance
    - `GET /api/settings/thresholds` → assert 5 thresholds (4 defaults + 1 custom)
    - `DELETE /api/settings/thresholds/{id}` → `GET` → assert 4 thresholds
    - **EXPECTED OUTCOME**: Tests PASS (confirms threshold persistence)
    - _Requirements: 2.9_

  - [x] 7.3 Verify preservation tests still pass
    - **Property 2: Preservation** - System Defaults Always Present
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - **EXPECTED OUTCOME**: Tests PASS (no regressions)

- [x] 8. Fix P1 — Wire context builder to real database queries

  - [x] 8.1 Rewrite `src/backend/intelligence/context_builder.py`
    - Change signature: `build_context(user_id: str) -> str`
    - Remove `from src.backend.intelligence.goal_tracker import ... _PENDING_CHECK_INS`; add `get_pending_check_ins`
    - Replace the hardcoded vitals string with a live query:
      ```python
      cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
      rows = conn.execute(
          "SELECT metric_type, value, unit, timestamp FROM health_metrics "
          "WHERE user_id=? AND timestamp >= ? ORDER BY timestamp DESC",
          (user_id, cutoff)
      ).fetchall()
      ```
      Group by `metric_type`; compute `min/max` for `heart_rate`, `latest` for `resting_heart_rate`, `hrv`, `spo2`. Fall back to `"No vitals data synced in the last 24h."` if empty.
    - Replace the hardcoded body composition string with:
      ```python
      row = conn.execute("SELECT * FROM body_compositions ORDER BY date DESC LIMIT 1").fetchone()
      ```
      Format as `"Last recorded X lbs, Y% body fat (DATE)."` or fall back to `"No body composition data recorded."` if None.
    - Replace the hardcoded calendar string with:
      ```python
      rows = conn.execute(
          "SELECT * FROM calendar_events WHERE date(start_time) = date('now') ORDER BY start_time"
      ).fetchall()
      ```
      Count events; scan `derived_signals` JSON for travel flag. Fall back to `"No calendar data synced."` if empty.
    - Replace `_PENDING_CHECK_INS` reference with `get_pending_check_ins(user_id)`
    - Update `get_active_goals()` call to `get_active_goals(user_id)`
    - _Bug_Condition: `build_context()` returns hardcoded strings regardless of DB contents_
    - _Expected_Behavior: `build_context(user_id)` queries `health_metrics`, `body_compositions`, `calendar_events` and returns real values_
    - _Preservation: alerts, goals, pending confirmations, and sync staleness sections of context unchanged_
    - _Requirements: 2.10_

  - [x] 8.2 Fix `src/backend/api/chat.py`
    - Change `context = build_context()` → `context = build_context(x_user_id)` in `generate_response()`
    - `x_user_id` is already in scope as a parameter of `chat_endpoint` and passed through to `generate_response`; update `generate_response` signature to accept `user_id` if needed, or pass it directly
    - _Bug_Condition: `build_context()` called without `user_id` argument_
    - _Expected_Behavior: chat responses reference real metric data for the authenticated user_
    - _Requirements: 2.10_

  - [x] 8.3 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - AI Context Contains Real Data
    - **IMPORTANT**: Re-run the SAME test from task 1 — do NOT write a new test
    - Seed a `health_metrics` row (`metric_type=resting_heart_rate`, `value=58`, `user_id=test_user`, `timestamp=now`) into the test DB
    - Seed a `body_compositions` row (`weight=175`, `body_fat_pct=18.5`, `date=today`)
    - Call `build_context("test_user")` → assert string contains `"58"` and does NOT contain `"52bpm"`
    - Call `build_context("test_user")` on empty DB → assert fallback strings present, no crash
    - **EXPECTED OUTCOME**: Tests PASS (confirms real data replaces hardcoded strings)
    - _Requirements: 2.10_

  - [x] 8.4 Verify preservation tests still pass
    - **Property 2: Preservation** - Context Structure and Other Sections Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - **EXPECTED OUTCOME**: Tests PASS (no regressions in intake/trends flows)

- [x] 9. Fix P1 — Wire LLM tools to real database queries

  - [x] 9.1 Rewrite `src/backend/intelligence/tools.py`
    - Import `_get_connection` from `src.backend.storage.sqlite_store`
    - Implement `get_body_composition(user_id: str, date_range: str) -> str`:
      Parse `date_range` into `start_date`; query `body_compositions` for that range; return `"N measurements. Latest: W lbs, F% body fat (DATE). 30-day change: ΔW lbs."` or `"No body composition data for this period."`
    - Implement `get_calendar_context(user_id: str, date_range: str) -> str`:
      Parse date range; query `calendar_events`; return formatted count, travel days, early/late event flags, or `"No calendar data for this period."`
    - Implement `compare_periods(user_id: str, metric: str, period_a: str, period_b: str) -> str`:
      Query `health_metrics` for `metric_type=metric` in both periods; compute averages; return `"[Metric] avg X in period_a vs Y in period_b (Z%)."`
    - Implement `get_correlations(user_id: str, metric_a: str, metric_b: str, days: int) -> str`:
      Query both metrics from `health_metrics` over `days` days; align by day; compute Pearson correlation; return `"[metric_a] and [metric_b] show [strength] [direction] correlation (r=R) over N days."`
    - Update `check_goal_progress(goal_id: str, user_id: str)` to call `get_active_goals(user_id)`
    - Update `suggest_goal(title, metric, target, direction, user_id: str)` to pass `user_id` to `suggest_goal_from_conversation`
    - Keep `query_metric()` and `pop_emitted_charts()` completely unchanged
    - _Bug_Condition: four tool functions return hardcoded placeholder strings_
    - _Expected_Behavior: each tool queries appropriate SQLite table and returns real data or explicit "no data" message_
    - _Preservation: `query_metric()` emits chart specs to `_EMITTED_CHARTS` unchanged; `pop_emitted_charts()` unchanged_
    - _Requirements: 2.11, 3.10_

  - [x] 9.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - AI Context Contains Real Data
    - **IMPORTANT**: Re-run the SAME test from task 1 — do NOT write a new test
    - Seed rows in `body_compositions`, `calendar_events`, and `health_metrics`
    - Call each tool with `user_id="test_user"` → assert returned strings contain seeded values, not placeholder text
    - Call each tool with empty DB → assert graceful "no data" strings returned, no crash
    - **EXPECTED OUTCOME**: Tests PASS
    - _Requirements: 2.11_

  - [x] 9.3 Verify preservation tests still pass
    - **Property 2: Preservation** - query_metric Chart Emission Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - Assert `query_metric()` still appends to `_EMITTED_CHARTS` and returns confirmation string
    - **EXPECTED OUTCOME**: Tests PASS (no regressions)

- [x] 10. Fix P1 — Implement real Google Calendar OAuth

  - [x] 10.1 Add Google credentials to `src/backend/config.py`
    - Add two new optional fields to the `Settings` class:
      ```python
      google_client_id: str | None = None
      google_client_secret: str | None = None
      ```
    - _Bug_Condition: `google_client_id` and `google_client_secret` not in Settings; OAuth functions mock_
    - _Expected_Behavior: credentials configurable via environment variables_
    - _Requirements: 2.12_

  - [x] 10.2 Create `.env.example` with Google credential placeholders
    - Create `.env.example` (or append if it exists) with:
      ```
      # GOOGLE_CLIENT_ID=
      # GOOGLE_CLIENT_SECRET=
      ```
    - _Requirements: 2.12_

  - [x] 10.3 Replace mock OAuth functions in `src/backend/importers/google_calendar.py`
    - Replace `get_auth_url(redirect_uri)`:
      Build `Flow` from client config using `settings.google_client_id` / `google_client_secret`; call `flow.authorization_url(access_type="offline")`; return `None` if credentials not configured
    - Replace `exchange_code(code, redirect_uri)`:
      Call `flow.fetch_token(code=code)`; return dict with `access_token`, `refresh_token`, `expires_in`
    - Replace `fetch_events(credentials_dict, start_time, end_time)`:
      Uncomment the real implementation already present in comments; build `Credentials` and `googleapiclient` service; call `service.events().list(...).execute()`
    - Keep `derive_signals()` and `parse_events()` completely unchanged
    - _Bug_Condition: mock functions return hardcoded fake tokens and empty event list_
    - _Expected_Behavior: `get_auth_url` returns real Google OAuth URL; `fetch_events` calls Google Calendar API_
    - _Preservation: `derive_signals()` and `parse_events()` signal derivation logic unchanged_
    - _Requirements: 2.12, 3.9_

  - [x] 10.4 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Google Calendar OAuth Produces Real Tokens
    - **IMPORTANT**: Re-run the SAME test from task 1 — do NOT write a new test
    - Without credentials: `get_auth_url("http://localhost/callback")` returns `None`
    - Unit test `fetch_events` with mocked `googleapiclient.discovery.build` → assert `service.events().list(...)` is called and items returned
    - **EXPECTED OUTCOME**: Tests PASS
    - _Requirements: 2.12_

  - [x] 10.5 Verify preservation tests still pass
    - **Property 2: Preservation** - derive_signals and parse_events Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - **EXPECTED OUTCOME**: Tests PASS (no regressions in calendar signal derivation)

- [x] 11. Fix P1 — Implement real Google Takeout zip parsing

  - [x] 11.1 Rewrite `src/backend/importers/takeout.py`
    - Replace the body of `parse_takeout_zip()` with a real parser
    - File pattern → metric type mapping:
      - `*heart_rate*` (excluding `*heart_rate_variability*` / `*hrv*`) → `MetricType.heart_rate`, value from `fitValue[0].value.fpVal`
      - `*step_count*` → `MetricType.steps`, value from `fitValue[0].value.fpVal`
      - `*heart_rate_variability*` or `*hrv*` → `MetricType.hrv`, value from `fitValue[0].value.fpVal`
      - `*calories*` → `MetricType.calories`, value from `fitValue[0].value.fpVal`
      - `*sleep_segment*` → `MetricType.sleep_duration`, value = `(int(endTimeNanos) - int(startTimeNanos)) / 1e9 / 60`
    - For each `Data Points` entry: parse timestamp from `startTimeNanos` via `datetime.fromtimestamp(int(v) / 1e9, tz=timezone.utc)`
    - Wrap each data point parse in `try/except` — log parse errors, continue to next point (do not abort)
    - Keep `process_takeout()` function signature and SQLite insert logic unchanged
    - _Bug_Condition: `parse_takeout_zip()` emits one fake record with `value: 65.0` per heart-rate file_
    - _Expected_Behavior: parser reads actual `fpVal` from JSON; supports all 5 metric types_
    - _Preservation: `process_takeout()` SQLite write logic unchanged; `BadZipFile` still raises `ValueError`_
    - _Requirements: 2.13_

  - [x] 11.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Takeout Parser Reads Actual Zip Payload
    - **IMPORTANT**: Re-run the SAME test from task 1 — do NOT write a new test
    - Build synthetic zip with `heart_rate.json` containing `{"Data Points": [{"fitValue": [{"value": {"fpVal": 72.0}}], "startTimeNanos": "1705123200000000000"}]}`
    - Assert returned record has `value == 72.0` (not `65.0`)
    - Build zip with `sleep_segment.json` entry with known start/end nanos → assert `metric == "sleep_duration"` and value is correct minutes
    - Assert malformed data points are skipped, not raised
    - **EXPECTED OUTCOME**: Tests PASS
    - _Requirements: 2.13_

  - [x] 11.3 Verify preservation tests still pass
    - **Property 2: Preservation** - process_takeout Write Logic Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - **EXPECTED OUTCOME**: Tests PASS (no regressions)

- [x] 12. Fix P2 — Fix test_chat.py wrong endpoint path

  - [x] 12.1 Fix `tests/test_chat.py`
    - Update `test_chat_endpoint` to use `Form(...)` style post: `client.post("/api/chat", data={"message": "Hi"}, headers={"X-User-ID": "test_user"})`
    - Extract `session_id` from the `POST /api/chat` response body: `data["session_id"]`
    - Replace `client.get("/api/chat/history")` → `client.get(f"/api/chat/sessions/{session_id}/history", headers={"X-User-ID": "test_user"})`
    - Assert response status is 200 and history contains the 2 expected messages (user + assistant)
    - _Bug_Condition: test calls `GET /api/chat/history` which returns 404; endpoint moved to `GET /api/chat/sessions/{session_id}/history`_
    - _Expected_Behavior: test calls correct endpoint and receives 200 with session history_
    - _Preservation: mock patching approach for httpx unchanged; assertion logic for chat response unchanged_
    - _Requirements: 2.14, 3.12_

  - [x] 12.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Test Suite Passes on Correct Endpoints
    - **IMPORTANT**: Re-run the SAME test from task 1 — do NOT write a new test
    - Run `pytest tests/test_chat.py -v` → assert no 404 errors, test passes
    - **EXPECTED OUTCOME**: Test PASSES
    - _Requirements: 2.14_

  - [x] 12.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Existing Tests Continue Passing
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - **EXPECTED OUTCOME**: Tests PASS (no regressions)

- [x] 13. Fix P2 — Fix guardrails to produce grammatical rewrites

  - [x] 13.1 Rewrite `src/backend/safety/guardrails.py`
    - Replace `PRESCRIPTIVE_PATTERNS` list and word-substitution loop with a sentence-level rewrite map:
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
    - Implement goal-aware suppression: split `llm_response` into sentences on `(?<=[.!?])\s+`; for each sentence, if any metric name from `active_goal_metrics` appears in `sentence.lower()`, skip rewrites for that sentence; otherwise apply all REWRITES patterns
    - Rejoin sentences with `" ".join(result)`
    - _Bug_Condition: `re.sub(pattern, "notable", ...)` produces malformed substitution; goal-aware suppression not implemented_
    - _Expected_Behavior: prescriptive phrases rewritten to grammatically correct neutral language; sentences with active-goal metrics left unchanged_
    - _Preservation: neutral text with no prescriptive phrases returned unchanged_
    - _Requirements: 2.15, 3.11_

  - [x] 13.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Guardrails Rewrites Produce Grammatical Sentences
    - **IMPORTANT**: Re-run the SAME test from task 1 — do NOT write a new test
    - `apply_guardrails("your HRV is too low")` → assert result contains `"below your recent baseline"` and does NOT contain `"notable"`
    - `apply_guardrails("your hrv is too low", active_goal_metrics=[MetricType.hrv])` → assert result unchanged (goal-aware suppression)
    - **EXPECTED OUTCOME**: Tests PASS
    - _Requirements: 2.15_

  - [x] 13.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Neutral Text Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - `apply_guardrails("Your readiness looks good.")` → assert unchanged
    - Property test: random strings with zero prescriptive phrases → assert unchanged
    - Property test: strings containing any prescriptive pattern → assert no occurrence of original pattern in output
    - **EXPECTED OUTCOME**: Tests PASS
    - _Requirements: 3.11_

- [x] 14. Fix P2 — Background uvicorn in make dev

  - [x] 14.1 Fix `Makefile` dev target
    - Change the `dev` target body to background uvicorn:
      ```makefile
      dev:
      	uvicorn src.backend.main:app --reload --host 0.0.0.0 --port 8000 &
      	cd src/frontend && npm run dev
      ```
    - Keep the `backend` and `frontend` phony targets unchanged for individual use
    - _Bug_Condition: `backend` target runs uvicorn synchronously; `frontend` target never executes_
    - _Expected_Behavior: `make dev` starts uvicorn in background then starts `npm run dev`_
    - _Preservation: `make test`, `make install`, `make reset-db` targets unchanged_
    - _Requirements: 2.16_

  - [x] 14.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - make dev Starts Both Services
    - `grep -A2 "^dev:" Makefile` → assert output contains `uvicorn` with `&`
    - **EXPECTED OUTCOME**: Test PASSES
    - _Requirements: 2.16_

  - [x] 14.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Other Makefile Targets Unchanged
    - `grep "^test:" Makefile` → assert `python -m pytest tests/ -v` unchanged
    - **EXPECTED OUTCOME**: Tests PASS (no regressions)

- [x] 15. Checkpoint — Ensure all tests pass
  - Run `python -m pytest tests/ -v` and confirm all tests pass
  - Run `python -c "import src.backend.main"` and confirm no import errors
  - Run `python -c "from src.backend.sync.scheduler import start_scheduler"` and confirm success
  - Verify `grep -A2 "^dev:" Makefile` shows `uvicorn ... &`
  - Ensure all tests pass; ask the user if questions arise

## Notes

- All tasks follow the observation-first exploratory methodology: property tests are written and run on unfixed code before any fix is applied.
- Tasks 1 and 2 are standalone property-based test tasks and must be completed before any implementation work begins.
- The `conftest.py` DB path isolation ensures test runs do not share SQLite state across test sessions.
- For Google Calendar OAuth (task 10), real credentials are required in `.env` for end-to-end verification; unit tests use mocked `googleapiclient.discovery.build`.
- The `make dev` fix (task 14) is a one-line Makefile change and does not affect `make test`, `make install`, or `make reset-db`.
- See `design.md` for full pseudocode of each `isBugCondition`, `expectedBehavior`, and Preservation Requirements referenced in task annotations.
