# Aegis Health Data Pipeline - Agent Handoff

## Current Architecture State

Aegis is being expanded into a comprehensive personal health copilot. The backend is built with FastAPI, Pydantic, and SQLite.

### Recently Implemented (Health Data & Intelligence Core)
- **Base Models**: `src/backend/models/health_metrics.py` contains the authoritative schema for time-series biometric data (`HealthMetric`), `BodyComposition`, `CalendarEvent`, and sync statuses.
- **Goal System**: `src/backend/models/goals.py`, `src/backend/intelligence/goal_tracker.py`, and `src/backend/api/goals.py`. This system tracks goals against incoming metrics, automatically calculates progress, and surfaces potential completions for confirmation.
- **Safety System**: `src/backend/models/safety.py`, `src/backend/safety/anomaly_detector.py`, `src/backend/safety/guardrails.py`, `src/backend/api/alerts.py`, and `src/backend/api/settings.py`. This detects anomalous metrics based on default or user-modified thresholds and creates alerts. It also prevents prescriptive AI language when goals are absent.

### Next Steps (as per `docs/IMPLEMENTATION_PLAN.md`)
- Fitbit API Integration (OAuth2 + Full Data Pull)
- FITINDEX Multi-Path Ingestion (CSV, Screenshot OCR, Manual Entry)
- Google Calendar Integration
- Sync Scheduler
- LLM Context Builder & Query Engine
- Interactive Dashboard UI
- Floating Chat Widget with STT Toggle

## Development Context

When working on this repository, please ensure that any new models use the Pydantic schemas defined in `src/backend/models/` and any database operations integrate cleanly with `src/backend/storage/sqlite_store.py`.

Refer to `docs/IMPLEMENTATION_PLAN.md` for the full breakdown of the target architecture.
