# aegis Product Specification

**Canonical product + architecture spec** (do not fork parallel specs).  
**Status date:** 2026-09-07  
**DoD:** `success_criteria.yaml`  
**Handoff:** `AGENT_HANDOFF.md`

---

## 1. Product identity (non-negotiable)

Aegis is a **daily training-decision copilot for functional longevity**.

Expanded product direction (same core, wider inputs):

> Aegis is a **local-first personal health copilot** that combines wearable data, body composition, calendar/lifestyle context, natural-language logging, image understanding, environmental context, health scoring, goal tracking, alerts, and a conversational dashboard — and still emits **one evidence-bound daily training directive**.

### Preserved daily-directive flow

```
Intake / synced health data
  → structured health records (with provenance)
  → evidence retrieval (today vs history)
  → health scores
  → WOD / training context (+ negotiation)
  → ONE evidence-bound daily directive
```

### Canonical health score model

| Score | Role |
|---|---|
| **Front-rack** | Mobility / front-rack readiness for loaded upper-body positions |
| **Sleep** | Overnight recovery quality |
| **Diet** | Fueling vs Macro Pool / nutrition targets |
| **Workout preparation** | Readiness to execute *today’s* training plan / WOD |
| **Overall health/fitness** | Derived summary from the four scores + selected wearable signals |

**Transitional implementation detail (current code):** the UI/API still expose temporary labels **`readiness`** and **`soreness`** (plus sleep/diet). Those are **not** the permanent product contract. Internal soreness may remain a *factor* feeding Front-rack and Workout preparation; it must not permanently replace Front-rack or Workout preparation as top-level scores.

---

## 2. Local-first boundary

| Concern | Where it runs |
|---|---|
| LLM inference, normalization, scoring, reasoning, storage | **Local** (Apple Silicon M2 home host; Ollama + SQLite) |
| Fitbit, Google Calendar | **External source connectors** (OAuth); data cached locally |
| Open-Meteo weather / AQI | **Optional external** environmental connector; cached locally |
| Cloud LLM / cloud DB | **Not required**; not on the core path |
| Offline / degraded demo | Must work with **fixtures + manual entry** when Fitbit, Calendar, weather, or AQI are unavailable |

**Privacy rules**

- Location is **opt-in**, **disabled by default**, **revocable**, **minimally stored**.
- Location / precise geo must **never** be sent to a cloud LLM.
- External API tokens stay on the local host; never embed secrets in the frontend bundle.

---

## 3. Repository audit vs “reported” functionality (critical)

This repository was audited on 2026-09-07 against the expanded feature list.

**Verified in this tree today**

- Text → structured intake → local scores → memory hits → daily directive
- FastAPI `/health`, `/api/intake`, `/api/directive`, `/api/logs/recent`
- SQLite hashing-vector memory (`backend/providers/memory.py`)
- Heuristic + optional Ollama text extraction
- Temporary scores: readiness / sleep / soreness / diet
- Simple text UI with Dictate button + Speak checkbox
- OS foundation success criteria `pass: true`
- Automated tests: **14 passed** (`make os-test`) — *not* 48/48 in this repo

**Listed as “current reported functionality” in planning input, but NOT present in this repository**

Fitbit OAuth; Google Fit / Takeout ZIP; FITINDEX CSV; chat UI; image attachments / thumbnails; Ollama `llava`; `AIContextProvider`; dashboard context; `dateparser`; Open-Meteo; geocoding / travel detection; health-log schema beyond intake logs; alert system; goals; Grafana-style dashboard; PWA; Tailscale docs; `make dev`; 48/48 tests.

Treat those items as **Planned product requirements**, not as implemented facts for this tree, until code + verify commands exist here.

> Passing automated tests only proves the **current suite** is green. It is **not** proof the full product specification is complete.

---

## 4. Status table (this repository)

Legend: **IT** = Implemented & tested · **IL** = Implemented but limited/incomplete · **P** = Planned · **B** = Blocked · **NV** = Not verified in this tree

| Area | Status | Notes |
|---|---|---|
| Local FastAPI boot + health | IT | `tests/test_health.py` |
| Text intake → `IntakeResult` | IT | Heuristic always; Ollama optional |
| Daily directive string | IT | Rule-based composer |
| Sleep / diet scorers | IT | Deterministic |
| Readiness / soreness scorers | IL | **Transitional labels**; not canonical contract |
| Front-rack score | P | Missing |
| Workout-preparation score | P | Missing |
| Overall health/fitness score | P | Missing |
| SQLite log store | IT | Restart durability + schema_version proven (Slice 0) |
| Memory retrieval | IL | Dedup + exclude-self + today/history/conflicts wired; relevance still basic |
| Evidence provenance | IT | source / recorded_at / quality / extractor / content_hash |
| Safety disclaimer | IT | API + UI (MVP-DISCLAIMER-01); broader PHC-SAFETY-01 still open |
| WOD negotiation | P | Parse only today |
| Macro Pool ledger | P | Meal-count heuristic only |
| Dictation UI control | IL | Browser API; not E2E verified |
| Opt-in TTS | IL | Often `tts: null`; not reliable |
| Fitbit OAuth + metrics | P / NV | Not in this tree |
| FITINDEX CSV / OCR / manual | P / NV | Not in this tree |
| Google Takeout import | P / NV | Future-compatible fallback |
| Google Calendar (read-only) | P / NV | Not in this tree |
| Chat + image + llava | P / NV | Not in this tree |
| LLM metric-query tools | P | Not in this tree |
| Inline charts | P | Not in this tree |
| Alerts / custom thresholds | P | Not in this tree |
| Goals + confirmation | P | Not in this tree |
| Sync registry / staleness | P | Not in this tree |
| Geolocation + weather/AQI | P | Not in this tree |
| Grafana-style dashboard | P | Current UI is single composer page |
| PWA / Tailscale remote | P | Not documented or implemented |
| Automated tests | IT | **23** passed in this tree (`make os-test` / pytest) |

---

## 5. Core training-directive contract (preserved)

Still required for MVP completion of the original Aegis identity:

1. Canonical four scores + overall score in API/UI.
2. Deduplicated evidence with **Today** vs **History** and conflict resolution (**today wins** by default).
3. WOD input + negotiation (`as_prescribed` | `scaled` | `substituted` | `deferred`).
4. Front-rack mobility path feeding score + negotiation.
5. Safety disclaimer on every directive.
6. Durable SQLite across restarts.
7. Optional voice that is honest about readiness (no silent `tts: null` when Speak is on without explanation).

---

## 6. Data ingestion requirements

### 6.1 Fitbit (OAuth connector)

Ingest and normalize at least:

- Heart rate, HRV, resting heart rate, SpO2  
- Sleep duration / minutes asleep  
- Steps, distance, active minutes, calories  
- Body weight, body-fat %  
- Stress score, breathing rate  
- Activities  

Requirements: real OAuth (no mock auth backdoor), encrypted/local token storage, graceful failure, fixture mode for demos.

### 6.2 FITINDEX body composition

Supported paths:

1. CSV upload  
2. Screenshot / image OCR (local vision, e.g. Ollama `llava` when available)  
3. Manual text entry  
4. **User review and correction before save** (mandatory)

### 6.3 Google Calendar (read-only)

Ingest: event name, location, description, start/end.  
Write access: **forbidden**. Revocable OAuth; local cache only.

### 6.4 Other intake

- Generic natural-language health logging (`/api/intake` and chat tools)  
- Generic file drop  
- Manual text entry  
- Google Health / Google Fit **Takeout ZIP** as **future-compatible fallback** (not primary)  
- Opt-in device geolocation (default off)  
- Environmental context via Open-Meteo weather + AQI  

---

## 7. Hybrid sync system

| Capability | Requirement |
|---|---|
| Background sync | Configurable interval; per-source enable/disable |
| On-demand sync | UI button + chat/voice command |
| Sync history | Last success, last attempt, error state, record counts / coverage |
| Retry | Bounded retries with backoff; never block local manual use |
| Staleness | Warn per source when last success > 24h |
| Degradation | App remains usable with manual entry + fixtures if Fitbit / Calendar / weather / AQI fail |

---

## 8. LLM health-data query layer

The local LLM **must not** receive the entire database in every prompt.

It queries SQLite through **structured tools**, including:

- List available metrics  
- Get latest value  
- Retrieve time series  
- Compare vs baselines  
- Summarize date ranges  
- Check source freshness  
- List active alerts  
- Query goal progress  
- Search conversation history  
- Retrieve evidence + provenance  

Example questions the system must support:

- “How has my resting heart rate changed this month?”  
- “How was my sleep over the last two weeks?”  
- “Have I made progress toward my body-fat goal?”  
- “What data is stale?”  
- “What changed before my readiness dropped?”  
- “What health data do you currently have?”  

Every answer must include **dates, sources, and limitations** where relevant.

---

## 9. Inline charts

LLM may return **validated chart specifications** (JSON schema), never arbitrary HTML/JS.

Chart types: metric trends, sleep, body composition, activity/load, goal progress, comparisons.

Must support: date ranges, tooltips, clickable points where practical, goal reference lines/bands, missing-data markers, source + timestamp display.

Frontend renders charts from the validated spec only.

---

## 10. Alerts and safety

### Default thresholds

- HR > 200 BPM  
- SpO2 < 90%  
- Resting HR > 15% above baseline  
- HRV > 30% below baseline  

### User controls

Override thresholds; disable alerts; create custom alerts; set severity; review history.

### Critical alert behavior

Prominent UI; available to assistant; proactive mention when relevant; include value, threshold, timestamp, source, data-quality caveats; suppress duplicates for unchanged events.

### Safety copy (required)

- Aegis does **not** diagnose medical conditions.  
- Aegis does **not** prescribe treatment.  
- Threshold alerts are **observations**, not diagnoses.  
- Training guidance is **non-medical decision support**.  
- Uncertain or stale data must be labeled.  
- Prefer neutral, factual wording over false certainty.

---

## 11. Goal planning

Goals may be created via UI form, natural language, or manual edit.

Fields: metric, target, direction, optional timeframe, success criteria, status, created_at, confirmation state, history.

Statuses: `in_progress` | `completed` | `abandoned` | `paused`.

Flow: detect possible completion → show evidence → **ask user to confirm** → mark complete only after confirmation; allow manual complete/abandon; **preserve history permanently**. Goals appear as chart reference lines/bands.

---

## 12. Interface and deployment

### Desktop dashboard (Grafana-style)

Daily directive, health scores, alerts, source freshness, interactive charts, goal progress, evidence/history, sync controls.

### Conversation

Floating chat; text input; optional Web Speech STT toggle; searchable history; image attachments; inline charts; screen context via `AIContextProvider`.  
**Text remains the reliable fallback.** Web Speech is never required.

### Deployment

- Home host: Apple Silicon M2  
- Local LLM + SQLite  
- Remote access via **Tailscale**  
- iPhone-installable **PWA**  
- API/DB **not** publicly exposed  

**Tailscale decision (resolved in spec):**

| Surface | Exposure |
|---|---|
| PWA / frontend | Serve on Tailscale **Serve** (mesh) to user devices; Funnel only if explicitly enabled for HTTPS convenience |
| API | Reachable only via authenticated Tailscale mesh (same MagicDNS host) behind local reverse proxy; session/token auth required |
| Funnel | If used, terminates TLS to a **local auth-aware reverse proxy** that serves the PWA and proxies `/api/*` — **never** exposes SQLite, Ollama, or raw internal ports |
| SQLite / Ollama | Bind localhost only; not Funnel targets |

---

## 13. Architecture (target modules)

```
frontend/          PWA + dashboard + floating chat
backend/
  intake/          NL + image → structured records
  connectors/      fitbit, calendar, fitindex, takeout, weather
  sync/            registry, jobs, staleness
  memory/          SQLite health DB + vector/evidence index
  scorers/         front_rack, sleep, diet, workout_prep, overall
  reasoner/        directive + tool-using chat
  alerts/          thresholds + history
  goals/           CRUD + confirmation
  charts/          validated chart specs
  obs/             local tracing
```

External connectors are adapters; core reasoning never hard-depends on them.

---

## 14. Implementation order (next)

1. Canonical schema, provenance, SQLite durability — **done (Slice 0)**  
2. Source registry + sync status ← **next**  
3. Complete manual/fixture ingestion  
4. Fitbit + Calendar adapters  
5. FITINDEX OCR/manual review workflow  
6. Alerts + staleness  
7. Goals + progress  
8. LLM query tools + inline charts  
9. Restore canonical four-score + WOD directive contract  
10. Mobile/PWA + Tailscale hardening  
11. End-to-end acceptance testing  

**First implementation slice after docs:** Slice 0 complete.  
**Next:** Source registry + sync status (fixture/manual sources; no OAuth yet).

---

## 15. Testing doctrine

| Layer | Proves |
|---|---|
| Unit tests | Function behavior |
| Integration tests | Connector/DB wiring with fixtures |
| E2E / acceptance | UI + API + persistence user journeys |
| Success criteria artifacts | DoD evidence only when `verify` passes |

UI presence ≠ backend implementation ≠ live integration ≠ E2E verification.

Requirements that still **lack tests in this repo** (non-exhaustive): Fitbit metric coverage, OAuth security, FITINDEX paths, Calendar, geolocation privacy, sync/staleness, LLM tools, charts, alerts, goals, conversation search, PWA, Tailscale, four-score contract, WOD negotiation, evidence dedup — see `PHC-*` / `MVP-*` rows in `success_criteria.yaml`.
