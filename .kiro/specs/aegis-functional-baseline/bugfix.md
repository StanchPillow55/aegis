# Bugfix Requirements Document

## Introduction

The Aegis application contains 12 bugs across three severity tiers that collectively prevent the app from starting, corrupt runtime data with hardcoded fakes, and silently discard all user data on every server restart. This document covers the full set of defects required to establish a working functional baseline: the server must start without import errors, all API endpoints must return real data, and all user-generated data (goals, alerts, thresholds) must survive restarts by being persisted to the SQLite database that already exists and is initialized by `init_db()`.

---

## Bug Analysis

### Current Behavior (Defect)

**P0 — App Won't Start**

1.1 WHEN the application is started THEN the server crashes with `ModuleNotFoundError` because `apscheduler`, `cryptography`, `google-auth`, `google-auth-oauthlib`, `google-api-python-client`, and `pytest-mock` are absent from `requirements.txt`

1.2 WHEN `src/backend/sync/scheduler.py` is imported THEN the import fails because `src/backend/sync/__init__.py` does not exist, making the `sync` package unresolvable

1.3 WHEN `GET /api/directive` is called THEN the endpoint crashes with `TypeError` because `get_log_by_date(date.today())` is called without the required `user_id` argument

1.4 WHEN `GET /api/directive` is called and a log exists THEN the endpoint crashes with `TypeError` because `get_similar_days(today_log, n=3)` is called without the required `user_id` argument

1.5 WHEN `GET /api/patterns/search` is called THEN the endpoint crashes with `TypeError` because `search_similar(query, n=n)` is called without the required `user_id` argument

1.6 WHEN `GET /api/logs` is called THEN the endpoint crashes with `TypeError` because `get_log_by_date(d)` is called without the required `user_id` argument

**P1 — Silent Data Loss / Wrong Behavior**

1.7 WHEN a user creates or modifies a goal THEN the goal is stored only in the module-level `_ACTIVE_GOALS` Python list in `goal_tracker.py` and is never written to the `goals` SQLite table, so all goals are lost on server restart

1.8 WHEN a safety alert is triggered THEN the alert is stored only in the module-level `_ACTIVE_ALERTS` Python list in `anomaly_detector.py` and is never written to SQLite, so all alerts are lost on server restart

1.9 WHEN a user creates or modifies a safety threshold THEN the threshold is stored only in the module-level `_MOCK_DB_THRESHOLDS` Python list in `settings.py` and is never written to the `safety_thresholds` SQLite table, so all user customizations are lost on server restart

1.10 WHEN the AI context is built for a chat response THEN `context_builder.py` returns hardcoded strings (`"HR 50-160bpm, Resting HR 52bpm"`, `"183 lbs, 21% body fat"`, `"3 meetings today"`) instead of querying the database, so the AI coach always responds based on fake data regardless of what has been synced

1.11 WHEN the LLM calls `get_body_composition()`, `get_calendar_context()`, `compare_periods()`, or `get_correlations()` as tools THEN each function returns a hardcoded placeholder string instead of querying the database, so the AI's tool-augmented responses contain no real data

1.12 WHEN a user initiates Google Calendar OAuth THEN `get_auth_url()` returns a hardcoded fake URL that is not a real Google OAuth authorization endpoint, and `exchange_code()` returns fake token strings (`"fake_google_access"`, `"fake_google_refresh"`), and `fetch_events()` always returns an empty list, so no calendar data is ever retrieved

1.13 WHEN a user uploads a Google Takeout zip containing health data THEN `parse_takeout_zip()` emits one fake record with `value: 65.0` per heart-rate file instead of parsing the actual data, and all other metric types (steps, sleep, HRV, activities) are ignored entirely

**P2 — Tests and Dev Tooling**

1.14 WHEN the test suite runs `test_chat.py` THEN the test calls `GET /api/chat/history` which does not exist (the real endpoint is `GET /api/chat/sessions/{session_id}/history`), causing the test to receive a 404 and fail

1.15 WHEN `apply_guardrails()` processes LLM output containing prescriptive phrases THEN it replaces phrases like `"you should"` and `"too high"` with the literal word `"notable"`, producing malformed sentences such as `"your HRV is notable"` instead of rewriting them meaningfully, and the goal-aware logic (suppress normative framing only when no goal is set for that metric) is not implemented

1.16 WHEN `make dev` is run THEN only the frontend starts because the `backend` target runs `uvicorn` synchronously without backgrounding it (`&`), so the `frontend` target never executes

---

### Expected Behavior (Correct)

**P0 — App Won't Start**

2.1 WHEN the application is installed via `pip install -r requirements.txt` THEN all six missing packages (`apscheduler==3.10.4`, `cryptography>=42.0.0`, `google-auth>=2.29.0`, `google-auth-oauthlib>=1.2.0`, `google-api-python-client>=2.130.0`, `pytest-mock>=3.14.0`) SHALL be present and installable without error

2.2 WHEN `src/backend/sync/scheduler.py` is imported THEN the import SHALL succeed because `src/backend/sync/__init__.py` exists and marks the directory as a Python package

2.3 WHEN `GET /api/directive` is called with an `X-User-ID` header THEN the endpoint SHALL extract the user ID from the header and pass it as the first argument to `get_log_by_date(user_id, date.today())`

2.4 WHEN `GET /api/directive` is called and a log exists THEN the endpoint SHALL pass the user ID to `get_similar_days(user_id, today_log, n=3)` without crashing

2.5 WHEN `GET /api/patterns/search` is called with an `X-User-ID` header THEN the endpoint SHALL pass the user ID to `search_similar(user_id, query, n=n)` without crashing

2.6 WHEN `GET /api/logs` is called with an `X-User-ID` header THEN the endpoint SHALL pass the user ID as the first argument to `get_log_by_date(user_id, d)` without crashing

**P1 — Silent Data Loss / Wrong Behavior**

2.7 WHEN a user creates, updates, or deletes a goal THEN the goal SHALL be written to and read from the `goals` SQLite table so that goals persist across server restarts

2.8 WHEN a safety alert is triggered THEN the alert SHALL be written to SQLite so that active alerts persist across server restarts

2.9 WHEN a user creates or modifies a safety threshold THEN the threshold SHALL be written to and read from the `safety_thresholds` SQLite table so that customizations persist across server restarts

2.10 WHEN the AI context is built THEN `context_builder.py` SHALL query the `health_metrics` and `body_compositions` tables for the most recent real data and include those values in the context string passed to the LLM

2.11 WHEN the LLM calls `get_body_composition()`, `get_calendar_context()`, `compare_periods()`, or `get_correlations()` as tools THEN each function SHALL query the appropriate SQLite table and return a summary of real data

2.12 WHEN a user initiates Google Calendar OAuth THEN `get_auth_url()` SHALL construct a real Google OAuth 2.0 authorization URL using the configured client credentials, `exchange_code()` SHALL exchange the authorization code for real tokens via the Google token endpoint, and `fetch_events()` SHALL call the Google Calendar API and return the actual event list

2.13 WHEN a user uploads a Google Takeout zip THEN the parser SHALL read and parse the actual JSON payload for each supported metric type (heart rate, steps, sleep, HRV, activities) and store the parsed records in the `health_metrics` table

**P2 — Tests and Dev Tooling**

2.14 WHEN `test_chat.py` runs THEN it SHALL call the correct endpoint path `GET /api/chat/sessions/{session_id}/history` and receive a 200 response

2.15 WHEN `apply_guardrails()` processes LLM output THEN it SHALL rewrite prescriptive phrases into neutral, observational language (e.g., `"your HRV is below your recent baseline"`) and SHALL suppress normative framing only for metrics that have no active user goal

2.16 WHEN `make dev` is run THEN the `backend` target SHALL start `uvicorn` in the background (with `&`) so that the `frontend` target also executes, and both services start concurrently

---

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a valid daily log is submitted via `POST /api/intake` THEN the system SHALL CONTINUE TO parse, score, and persist the log to SQLite exactly as before

3.2 WHEN `GET /api/trends` is called with a valid date range and user ID THEN the system SHALL CONTINUE TO return the score time-series from the `score_history` table

3.3 WHEN `GET /api/directive` returns a recommendation THEN the system SHALL CONTINUE TO apply the same rule-based readiness, soreness, sleep, and hydration directives as before — only the data-fetching call signature changes

3.4 WHEN `GET /api/patterns/performance-predictors` or `GET /api/patterns/insight` is called THEN the system SHALL CONTINUE TO invoke the existing `day_before_performance()` and `generate_weekly_insight()` functions without modification

3.5 WHEN `GET /api/goals` is called THEN the system SHALL CONTINUE TO return the full list of goals with the same response shape defined by the `Goal` Pydantic model

3.6 WHEN `POST /api/goals/{goal_id}/complete` or `POST /api/goals/{goal_id}/confirm-completion` is called THEN the system SHALL CONTINUE TO update goal status and `completed_at` as before, now also persisting the change to SQLite

3.7 WHEN `GET /api/settings/thresholds` is called on a fresh server start THEN the system SHALL CONTINUE TO return the four system-default thresholds (heart rate >200, SpO2 <90, resting HR delta >15%, HRV delta <-30%) — these defaults must be seeded into SQLite if the table is empty

3.8 WHEN `check_metric_against_thresholds()` triggers an alert THEN the system SHALL CONTINUE TO return an `Alert` object and update the acknowledged state via `acknowledge_alert()`, now with SQLite backing

3.9 WHEN the Google Calendar `derive_signals()` and `parse_events()` functions receive a list of real events THEN the system SHALL CONTINUE TO derive the same early-morning, late-night, travel, and busy-day signals without modification

3.10 WHEN the LLM `query_metric()` tool is called THEN the system SHALL CONTINUE TO emit a chart spec to `_EMITTED_CHARTS` and return a confirmation string as before

3.11 WHEN `apply_guardrails()` is called with output that contains no prescriptive phrases THEN the system SHALL CONTINUE TO return the original string unchanged

3.12 WHEN `make test` is run THEN the system SHALL CONTINUE TO discover and run all tests under `tests/` using pytest with the existing `conftest.py` DB path isolation
