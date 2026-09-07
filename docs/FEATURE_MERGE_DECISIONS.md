# Feature Merge Decisions

**Date:** 2026-09-07  
**Target:** current Cursor workspace (`/workspace`)  
**Older prototype:** `/Users/bradleyharaguchi/Downloads/aegis` (**not readable on Cloud Agent**)

---

## 1. Architectural decisions

| Decision | Choice | Rationale |
|---|---|---|
| Canonical architecture | **Current workspace** FastAPI + SQLite + local providers + static frontend | Passing tests, Slice 0–6 already land; PRODUCT_SPEC local-first |
| Older tree role | Read-only feature source | Must not overwrite target history or break tests |
| Merge style | Semantic port, not `git merge` | Paths/layouts differ; blind copy would destroy contracts |
| Cloud APIs | Optional connectors; never required for boot | User local-only direction; fail soft with **clear disabled/config state** |
| Fixtures | Allowed for tests/demos | Must be labeled `fixture` / `offline` — never presented as live sync success |
| Fake OAuth / mock auth | **Forbidden** | PRODUCT_SPEC + PHC-OAUTH-01 |
| Voice | Browser STT/TTS optional; Deepgram out of core | Local-first |
| Score contract | Front-rack, Sleep, Diet, Workout-prep, Overall | Transitional readiness/soreness may remain internal factors only |

---

## 2. Conflicts and resolutions

| Conflict | Resolution |
|---|---|
| Older prototype unreachable on agent | Document blocker; continue independent ports from PRODUCT_SPEC + matrix; re-audit when tree provided |
| PRODUCT_SPEC §3–4 status table stale vs code | Refresh status table to match AGENT_HANDOFF + matrix |
| Macro Pool exists only in tests | Wire into production diet/canonical scoring |
| Takeout ZIP parser only in tests | Promote to `backend/connectors/takeout.py` + API |
| `/api/environment` always returns ok fixture | Distinguish `live` vs `offline_fixture` vs `disabled`; never imply live success when offline |
| Fitbit “sync success” via fixture while OAuth missing | Expose `auth_state=needs_credentials|fixture_mode`; UI must not say “connected to Fitbit” for fixture |
| Chat/vision “reported” features absent | Implement minimal real chat+tools; vision status honest if llava absent |
| Grafana full dashboard vs composer | Ship **light dashboard** (sync/alerts/goals/charts) now; defer full Grafana clone |
| Legacy Redis/Fetch/Browserbase modules | Leave quarantined; do not make them boot-required |

---

## 3. Migrations performed this run

1. `docs/FEATURE_MERGE_MATRIX.md` + this decisions doc.  
2. Takeout ZIP → `backend/connectors/takeout.py` + `/api/takeout/zip`.  
3. Macro Pool → `backend/scorers/macro_pool.py` wired into diet + canonical scores.  
4. Open-Meteo client with `mode=live|offline|disabled` (never claims live when offline).  
5. Connector honesty: `integration_state` + `live_oauth=false` on `/api/sources`.  
6. Frontend overview (sync/env/alerts/chart), settings/imports, floating chat dock.  
7. Chat service + `/api/context/screen` + `/api/vision/status` + date parsing tool.  
8. `make dev` alias → `make os-dev` (single startup path).  
9. PRODUCT_SPEC / AGENT_HANDOFF updates.

---

## 4. Intentionally deferred

| Feature | Why deferred |
|---|---|
| Live Fitbit OAuth token exchange | Requires user secrets + redirect URI; show `needs_credentials` instead |
| Live Google Calendar OAuth | Same |
| FITINDEX OCR / llava screenshot pipeline | Needs local vision model + UX review loop; CSV/manual already ship |
| Full Grafana-style multi-page analytics | Large UI rewrite; light dashboard first |
| Deepgram voice-first | Conflicts with local-first decision |
| Calendar travel detection | Needs live calendar + geo consent path |
| Playwright E2E against live `os-dev` | Optional hardening; CI uses TestClient |
| Re-inspection of older Downloads tree | **Blocked** until user provides zip/repo/sync |

---

## 5. Credentials / permissions blockers

When available, wire without fake success:

- `FITBIT_CLIENT_ID`, `FITBIT_CLIENT_SECRET`, `FITBIT_REDIRECT_URI`
- Google Calendar OAuth client JSON
- Optional: nothing required for Open-Meteo (no key), but network egress must work

Until then: UI/API must report **disabled / needs_credentials / offline_fixture**.

---

## 6. Definition of “aggregate complete” for this agent pass

- Matrix + decisions committed.  
- Independent ports above implemented + tested.  
- No fake live integrations.  
- Older-prototype unique features marked **U** until the tree is supplied; then a follow-up pass updates the matrix and ports residuals.

### Evidence (this pass)

| Check | Result |
|---|---|
| Local `make os-test` | 94 pytest passed |
| GitHub CI on `cursor/feature-merge-aggregate-766c` @ `2342e0a` | **success** (2 checks) |
| PR | https://github.com/StanchPillow55/aegis/pull/29 |
| Older prototype inspection | Still blocked (path not on agent) |
