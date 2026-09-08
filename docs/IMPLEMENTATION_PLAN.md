# Aegis Implementation Plan — next agent handoff

**Canonical branch:** `cursor/feature-merge-aggregate-766c` · [PR #29](https://github.com/StanchPillow55/aegis/pull/29)  
**Base for new work:** prefer stacking on #29 (or merge #22–#29 into `master` first if the operator chooses)  
**DoD:** `success_criteria.yaml` · Spec: `docs/PRODUCT_SPEC.md` · Matrix: `docs/FEATURE_MERGE_MATRIX.md`  
**Date:** 2026-09-08

---

## 0. Where we are (one paragraph)

Aegis is a **local-first** daily training-decision / personal health copilot. The Cloud Agent workspace holds the canonical FastAPI + SQLite + static frontend app. Stacked slices **#22–#28** plus feature-aggregation **#29** are CI-green. Legacy prototype is mirrored read-only from `origin/legacy-aegis` → `/workspace/legacy-aegis`. Compatible residuals are already ported; remaining work is mostly **live OAuth**, **UI depth**, and **E2E** — not core schema.

---

## 1. Completed progress (stacked PRs)

| Slice | PR | Result |
|---|---|---|
| OS local foundation + text UI | #22 | CI green |
| MVP / PRODUCT_SPEC expansion | #23 | CI green |
| 0 Schema / evidence / disclaimer | #24 | CI green |
| 1 Source registry + sync | #25 | CI green |
| 2–5 Metrics ingest + fixture connectors | #26 | CI green |
| 6–11 Scores, WOD, alerts, goals, tools, charts, PWA, Tailscale docs | #27 | CI green |
| BUG-LOCALHOST-01 docs + Makefile/os-health | #28 | CI green |
| Feature aggregate + legacy residual ports | #29 | CI green (`f8a3fed`) |

### Verification (current tip of #29)

| Check | Result |
|---|---|
| `make os-test` | **103** pytest collected/passed |
| `success_criteria.yaml` | **43/43** `pass: true` |
| Live Open-Meteo | `mode=live` (egress approved) |
| Demos | `make mvp-demo` / `make os-demo` |

---

## 2. Functionality map (what works today)

### Core training directive
- Text intake → heuristic/Ollama extract → evidence (today/history/conflicts, today_wins)
- Canonical scores: **Front-rack / Sleep / Diet / Workout-prep / Overall**
- Macro Pool blended into diet when `protein_g` present
- Optional **hydration / performance factors** (not top-level contract)
- WOD negotiation + safety disclaimer on every directive
- Durable SQLite memory + health metrics stores

### Ingestion & sync
- Source registry, enable toggles, on-demand sync, 24h staleness
- Fixture Fitbit / Calendar / Takeout (labeled fixture — not live OAuth)
- FITINDEX CSV + manual review/confirm gate
- FITINDEX screenshot OCR draft (`/api/fitindex/ocr`) when local llava present
- FITINDEX NL text heuristic draft
- Google Takeout ZIP: **CSV + JSON Data Points**
- Manual metric logs

### Environment & honesty
- Geo default-off; never sent to cloud LLM
- Open-Meteo `live|offline|disabled` (no silent fake “live”)
- Fitbit OAuth scaffold: `/api/fitbit/status|auth|callback` — `needs_credentials` until secrets
- Connector `integration_state` / `live_oauth=false` on `/api/sources`

### Intelligence & chat
- Floating chat dock + sessions + guardrails
- Rich `/api/context/screen` (vitals, alerts, goals, stale, calendar)
- LLM tools: metrics, alerts, goals, freshness, body_comp, calendar_context, correlate, trend, parse_date
- Patterns API: `/api/patterns/trend|weekly|correlate|predictors`
- Calendar lifestyle signals (early/late/busy/travel)
- Chart **specs** + SVG renderer in overview
- PWA manifest (thin); Tailscale security contract documented

### UI surfaces
- Composer (Dictate / Speak / Get directive)
- Overview: sync panel, environment, alerts/goals, metric chart
- Settings: Fitbit status, FITINDEX CSV/OCR, Takeout ZIP, Add log
- Chat dock with image preview

### Dev UX
```bash
make os-dev    # alias: make dev → http://127.0.0.1:8000/
make os-health # same-host proof
make os-test
```
**Browser rule:** Cloud Agent loopback ≠ laptop Chrome → `docs/bugs/BUG-LOCALHOST-01.md`.

---

## 3. Honest gaps (documented, not “broken”)

| Gap | Status | Blocker |
|---|---|---|
| Live Fitbit metric pull after OAuth | Scaffold only | `FITBIT_CLIENT_*` + browser callback + token pull |
| Live Google Calendar OAuth | Deferred | Google client secrets |
| llava OCR in real demos | Code ready | Local Ollama `llava` model |
| Full Grafana / Vite SPA dashboard | Deferred by design | Product chose static single-process UI |
| PWA service worker + icons | Thin manifest | Follow-on polish |
| Playwright E2E vs live `os-dev` | Missing | Scope + same-host browser |
| Operator Tailscale mesh | Docs only | Operator machine setup |
| Chroma / multi-user | Intentionally skipped | Local-first single-user DoD |
| PR merge stack #22–#29 → `master` | Still open drafts | Human merge/order |

---

## 4. Next features to develop (priority order)

### P0 — Operator / merge hygiene
1. **Merge stack** `#22 → #29` into `master` (or rebase #29 onto latest preferred base) so one tip is canonical.  
2. Close or supersede #30 if it only shared the legacy snapshot (legacy already on `legacy-aegis`).

### P1 — Live connectors (secrets-gated)
3. **Fitbit live pull:** after successful OAuth, map sleep/HRV/HR/SpO2/activity/weight into `HealthMetricsStore` with provenance `fitbit` + rate limit; keep fixture path.  
4. **Google Calendar live read-only:** OAuth + event fetch → `calendar_event` metrics + `derive_calendar_signals`; never claim connected without tokens.  
5. Secrets in `.env` / Cloud secrets: document exact callback URIs for local `8000`.

### P2 — UI / product depth (no SPA rewrite required)
6. **Goals & alerts editors** in Settings (CRUD already exists in API).  
7. **Chart goal bands** rendered on SVG (API already returns `goal_bands`).  
8. **FITINDEX confirm UI** (draft → edit → confirm) instead of API-only confirm.  
9. **PWA:** icons + minimal service worker for installability.  
10. Persist chat sessions to SQLite (today: in-memory process local).

### P3 — Quality / E2E
11. **Playwright** smoke: open `/`, submit intake, see scores (run on same host as server).  
12. Optional background sync loop behind `SyncConfig.background_enabled` (no APScheduler required at boot).  
13. Intake heuristic extraction for hydration/performance fields from free text.

### Do not do (unless product reverses)
- Restore fake OAuth / silent fake weather  
- Require Redis, Deepgram, Anthropic, Browserbase for boot  
- Replace SQLite memory with Chroma as DoD  
- Blind `git merge` of `legacy-aegis` into canonical history  
- Modify remote `legacy-aegis` branch

---

## 5. Suggested next-agent slices

| Slice ID | Scope | Exit criteria |
|---|---|---|
| **A** | Merge/rebase hygiene for #22–#29 | One green tip on preferred base; handoff updated |
| **B** | Fitbit live pull behind secrets | OAuth round-trip + ≥1 real metric written **or** clear blocked-on-secrets artifact |
| **C** | Goals/alerts/FITINDEX confirm UI | Manual click-path + TestClient coverage |
| **D** | Playwright smoke | CI job or documented local script green on same host |
| **E** | Calendar live (optional) | Same honesty pattern as Fitbit |

Default recommendation for a fresh agent: **start at Slice A, then C** (UI depth without secrets). Do **B/E** only when Fitbit/Google secrets are present.

---

## 6. Commands cheat sheet

```bash
# bootstrap
python3 -m pip install -r requirements.txt
make os-test

# run UI on the SAME machine as the browser
make os-dev          # http://127.0.0.1:8000/
make os-health

# refresh legacy mirror (read-only)
git fetch origin legacy-aegis
rm -rf /workspace/legacy-aegis && mkdir -p /workspace/legacy-aegis
git archive origin/legacy-aegis | tar -x -C /workspace/legacy-aegis

# never
git push origin legacy-aegis   # DO NOT
```

---

## 7. Key paths

| Area | Path |
|---|---|
| App | `backend/main.py` |
| Scores | `backend/scorers/canonical.py` |
| Sync | `backend/sync/registry.py` |
| Connectors | `backend/connectors/` |
| Chat | `backend/chat/` |
| Frontend | `frontend/{index.html,app.js,styles.css}` |
| Legacy mirror | `/workspace/legacy-aegis` (gitignored) |
| Localhost bug | `docs/bugs/BUG-LOCALHOST-01.md` |
| Matrix | `docs/FEATURE_MERGE_MATRIX.md` |
