# Aegis Implementation Plan — next agent handoff (QA-revised)

**Canonical branch:** `cursor/feature-merge-aggregate-766c` · [PR #29](https://github.com/StanchPillow55/aegis/pull/29)  
**Base for new work:** stack on #29 (or merge #22–#29 into `master` first)  
**DoD:** `success_criteria.yaml` · Maturity map: `docs/SC_MATURITY.md` · Spec: `docs/PRODUCT_SPEC.md` · Matrix: `docs/FEATURE_MERGE_MATRIX.md`  
**Date:** 2026-09-08 (revised after QA review)  
**Tip when written:** `b04f0fa`+

---

## 0. Where we are (honest)

Aegis is a **local-first** daily training-decision / personal health copilot on FastAPI + SQLite + static frontend. Stacked PRs **#22–#29** are CI-green and deliver a working foundation: schema/evidence, sync registry, fixture connectors, canonical scores, alerts/goals APIs, chat dock, light dashboard, legacy residual ports.

**What is NOT done:** operational completion — required background sync, full live Fitbit/Calendar parity + OAuth security, persistent/searchable chat, interactive Grafana-style charts, geo consent UI, authenticated remote/PWA install, and true E2E verification. Treat `pass: true` in `success_criteria.yaml` as **automated verify green**, not product-complete; see §1.1 and `docs/SC_MATURITY.md`.

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
| Feature aggregate + legacy residual ports | #29 | CI green |

### Verification (foundation layer)

| Check | Result | Meaning |
|---|---|---|
| `make os-test` | **103** pytest passed | Unit/integration contracts green |
| `success_criteria.yaml` `pass: true` | **43/43** | Automated `verify` commands pass — **not** all live/E2E complete |
| Live Open-Meteo | `mode=live` | Real network path works when egress allowed |
| Demos | `make mvp-demo` / `make os-demo` | Scripted demos OK |

### 1.1 Success-criteria maturity (required reading)

Do **not** claim live Fitbit, remote access, or full chat complete because a scaffold/fixture/docs exists.

| Maturity | Meaning |
|---|---|
| `verified` | Real path exercised end-to-end in intended environment |
| `fixture-verified` | Deterministic fixtures/tests prove shape + honesty; not live provider |
| `implemented-but-not-E2E-tested` | Code/UI present; no Playwright/mobile acceptance |
| `blocked-on-secrets` | Code ready; needs OAuth client secrets / browser callback |
| `planned` | Specced in this plan; not shipped |

Full ID map: **`docs/SC_MATURITY.md`**. Next agent should update that map when maturity improves, and only flip narrative “complete” when maturity ≥ `verified` (or `fixture-verified` when fixture is the accepted permanent mode).

---

## 2. Functionality map (what exists today)

### Core training loop
- Text intake → heuristic/Ollama extract → evidence (today/history/conflicts, today_wins)
- Canonical scores: Front-rack / Sleep / Diet / Workout-prep / Overall (+ Macro Pool)
- Optional hydration/performance **factors**
- WOD negotiation + safety disclaimer
- Durable SQLite memory + health metrics

### Ingestion & sync (partial vs product requirement)
- Source registry, per-source enable, on-demand sync, last-success + 24h stale flags — **fixture-verified**
- **Background scheduled sync:** required loop shipped (S1) — interval, retries, fail-soft boot, UI/chat/voice triggers — **fixture-verified** (Playwright E2E still open)
- Fixture Fitbit / Calendar / Takeout — **fixture-verified**
- FITINDEX CSV + manual review API; OCR draft when llava present — **implemented-but-not-E2E**
- Takeout CSV + JSON Data Points — **I**

### Environment & connectors
- Geo default-off API contract — **fixture-verified**; **UI consent/revoke/home/threshold missing** → P2
- Open-Meteo live/offline/disabled — **verified** (live smoke)
- Fitbit OAuth scaffold (status/auth/callback) — **blocked-on-secrets** / incomplete security checklist
- Calendar signals on stored events — **I**; live Google OAuth — **planned**

### Intelligence & chat (partial)
- In-memory chat sessions + guardrails + screen context — **implemented-but-not-E2E**
- Tools/patterns APIs exist — chat UI does not fully drive tools/charts yet
- Chart specs + basic SVG — **not** Grafana-style interactive yet
- PWA: thin manifest only; Tailscale: **docs only**

### Safety output model (clarified — implement in copy + reasoner)

Two distinct outputs; do not conflate:

1. **Health analysis** — factual/observational only; guardrails suppress unsupported prescriptive language; no diagnosis.  
2. **Training planning (directive)** — optional, clearly labeled **non-medical decision support**; WOD negotiation may propose intensity/substitutions; require user confirmation when changing plan materially; always show disclaimer.

Never claim “observational only” while emitting unmarked commands like “hit today’s plan with normal intensity” without the training-planning label + disclaimer.

---

## 3. Gaps raised by QA (must address)

| # | Issue | Plan response |
|---|---|---|
| 1 | Background sync marked optional | **Promote to required P1** |
| 2 | Fitbit metric list incomplete | Full metric matrix in §4.1 |
| 3 | OAuth security under-specified | Full checklist in §4.2 (Fitbit + Calendar) |
| 4 | Chat incomplete | Persist/search/images/llava/tools/inline charts/context tests — P1 |
| 5 | Goals/alerts E2E incomplete | NL goals, statuses, history, custom alerts, proactive chat — P1/P2 |
| 6 | Dashboard quietly reduced | Keep static stack but require Grafana-style interactions — P2 |
| 7 | Remote mostly docs | Authenticated Tailscale remote + PWA install tests — P2 |
| 8 | Geo privacy needs UI | Consent/revoke/delete/home/threshold — P2 |
| 9 | Safety policy conflict | Dual output model above — enforce in reasoner/UI |
| 10 | `43/43 pass` misleading | Maturity map; do not over-claim |

---

## 4. Priority backlog (QA-aligned)

### P0 — Merge hygiene
1. Merge/rebase `#22–#29` onto preferred base.  
2. Supersede/close #30 if redundant with `legacy-aegis`.

### P1 — Operational completion (required)

#### 4.1 Background sync (**required**, not optional)
- Configurable interval (`SyncConfig.interval_seconds`)
- Per-source enable/disable
- Automatic background loop when `background_enabled=true` (fail-soft; no boot hang)
- Retry/backoff on failure
- Last-successful-sync tracking (already partial)
- Source-specific stale warnings (UI + chat)
- On-demand sync via: **button**, **chat**, **voice/dictate command**
- Tests: schedule tick, retry, stale, disabled source skipped

#### 4.2 Fitbit live ingestion + OAuth security
**Metrics (each with units, timestamps, source, confidence/quality, provenance):**
- Heart rate, HRV, **resting HR**, SpO2
- Sleep duration / minutes asleep
- **Steps, distance, active minutes, calories**
- **Body weight, body-fat %**
- **Stress score, breathing rate**
- **Activities** (sessions/minutes)
Keep fixture path for CI. Live path **blocked-on-secrets** until clients exist.

**OAuth security (Fitbit + Google Calendar):**
- OAuth `state` validation
- Callback validation / redirect-error handling
- Token refresh + expiry handling
- Token revocation / disconnect UX
- Least-privilege scopes
- Encrypted local token storage (`AEGIS_TOKEN_KEY` / Fernet; never hardcoded demo seed as production)
- No credentials/tokens in logs
- Clear UI states: `disconnected | needs_credentials | authorizing | connected | error | token_expired`
- Tests: mocked provider OAuth; assert no mock auth backdoors

#### 4.3 Chat completion
- SQLite-persisted conversations (survive restart)
- Searchable conversation history (tool + UI)
- Image persistence or safe local file refs (not only data-URL in RAM)
- Full **llava** image-processing click path (FITINDEX + chat)
- LLM query tools invoked from chat UI (not only heuristic intent)
- **Inline chart rendering inside chat** from validated chart specs
- Screen-context regression tests

#### 4.4 Goals & alerts E2E
- Goal creation from **natural-language chat**
- Statuses: `in_progress | completed | abandoned | paused`
- Confirmation before automatic completion
- Goal history preservation
- Custom alert creation for any supported metric
- Alert history + critical-alert **deduplication**
- Proactive alert mentions in chat
- Tests for stale, missing, and conflicting data

### P2 — UI, remote, geo, calendar live

#### 4.5 Interactive dashboard (static stack OK; Grafana-style behavior required)
Not a full Vite/Grafana rewrite, but must include:
- Clickable charts
- Date-range controls
- Tooltips
- Goal lines/bands
- Missing-data indicators
- Source + timestamp display
- Inline charts in chat (ties to §4.3)

#### 4.6 Google Calendar live
- Live OAuth + read-only ingest (name, location, description, start/end)
- Signal derivation (early/late/busy/travel)
- Same OAuth security checklist as Fitbit

#### 4.7 FITINDEX confirmation UI
- Draft → edit → confirm in Settings (API already gates confirm)

#### 4.8 Geolocation privacy UI
- Permission prompt
- Enable/disable control
- Revocation behavior
- Stored-location deletion
- Home-location configuration
- Travel-distance threshold configuration
- Assert never transmitted to cloud LLMs (tests)

#### 4.9 Remote experience + PWA
- Authenticated remote access (Tailscale recommended; **no Funnel / no public DB**)
- Frontend/API routing decision documented + implemented
- No direct database exposure
- Mobile browser acceptance test
- PWA service worker + icons
- iPhone installation test
- Secure cookies / CORS / CSRF / rate-limit handling as applicable to local+Tailscale topology

### P3 — Verification depth
- Playwright E2E on **same host** as `os-dev`
- OAuth integration tests with mocked providers
- Offline / source-failure tests
- M2 performance + local-model resource tests
- SQLite backup/export/restore testing for health data

### Do not do
- Fake OAuth / silent fake weather  
- Boot-required Redis/Deepgram/Anthropic/Browserbase  
- Chroma as DoD replacement for SQLite memory  
- Blind git merge of `legacy-aegis`  
- Modify remote `legacy-aegis`  
- Mark live integrations `verified` without live/E2E evidence  

---

## 5. Suggested next-agent slices (revised)

| Slice | Scope | Exit criteria |
|---|---|---|
| **A** | Merge hygiene #22–#29 | Single preferred tip green |
| **S1** | Required background sync loop + tests + UI/chat/voice triggers | **DONE** (`artifacts/s1-background-sync.txt`) — config interval; retries; stale; on-demand three channels |
| **S2** | Chat SQLite persist + search + inline charts + context tests | Restart-durable history; searchable; chart in bubble |
| **S3** | Goals NL extract + statuses/history + alert custom/dedupe + proactive chat | E2E TestClient + UI path |
| **S4** | Interactive charts (click/range/tooltip/bands/missing/source) | Manual + automated UI checks |
| **S5** | Fitbit full metric map + OAuth security checklist | Live **or** `blocked-on-secrets` artifact; mocked OAuth tests green |
| **S6** | Geo consent UI + Calendar live OAuth | Privacy UX + honesty states |
| **S7** | PWA SW/icons + Tailscale authenticated remote acceptance | Mobile install notes + checklist artifact |
| **S8** | Playwright + offline/failure + backup/restore | Documented green runs |

**Recommended start without secrets:** **S2 → S3 → S4** (S1 done on `cursor/s1-background-sync-3696`).  
**With Fitbit secrets:** insert **S5** next.  
**With Google secrets:** **S6**.

---

## 6. Commands

```bash
python3 -m pip install -r requirements.txt
make os-test
make os-dev          # SAME machine as browser → http://127.0.0.1:8000/
make os-health

# legacy mirror (read-only)
git fetch origin legacy-aegis
rm -rf /workspace/legacy-aegis && mkdir -p /workspace/legacy-aegis
git archive origin/legacy-aegis | tar -x -C /workspace/legacy-aegis
```

Localhost trap: `docs/bugs/BUG-LOCALHOST-01.md`.

---

## 7. Key paths

| Area | Path |
|---|---|
| App | `backend/main.py` |
| Sync | `backend/sync/registry.py` |
| Fitbit OAuth | `backend/connectors/fitbit_oauth.py` |
| Chat | `backend/chat/` |
| Safety dual-output | `backend/reasoner/`, `backend/safety/guardrails.py` |
| Frontend | `frontend/` |
| Maturity map | `docs/SC_MATURITY.md` |
| Matrix | `docs/FEATURE_MERGE_MATRIX.md` |
| Legacy | `/workspace/legacy-aegis` (gitignored) |
