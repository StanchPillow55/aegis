# aegis Product Specification

**Canonical product + architecture spec** (do not fork parallel specs).  
**Status date:** 2026-09-08  
**DoD:** `success_criteria.yaml`  
**Handoff:** `AGENT_HANDOFF.md`  
**Goal Graph:** `docs/GOAL_GRAPH.md`  
**Implementation plan:** `docs/IMPLEMENTATION_PLAN.md`

---

## 1. Product identity (non-negotiable)

Aegis is a **daily training-decision copilot for functional longevity**.

Expanded product direction (same core, wider inputs):

> Aegis is a **local-first personal health copilot** and a **living evidence-backed goal system**: wearable data, body composition, calendar/lifestyle context, natural-language logging, image understanding, environmental context, **pluggable health signals**, goal/task hierarchy, alerts, and a conversational dashboard — still able to emit **one evidence-bound daily training directive**.

### Preserved daily-directive flow

```
Intake / synced health data / journal
  → structured health records (with provenance)
  → evidence retrieval (today vs history)
  → goal-relevant signals (+ optional overall)
  → WOD / training context (+ negotiation) when planning
  → ONE evidence-bound daily directive (when requested)
  → goal/task suggestions (human-in-the-loop)
```

### Signal model (replaces permanent fixed score cards)

**Front-rack, Sleep, Diet, Workout preparation** remain available as **analyzers / signal providers**. They are **not** permanent top-level product categories.

| Signal | Role when relevant |
|---|---|
| **Front-rack** | Mobility / front-rack readiness for loaded upper-body positions |
| **Sleep** | Overnight recovery quality |
| **Diet** | Fueling vs Macro Pool / nutrition targets |
| **Workout preparation** | Readiness to execute *today’s* training plan / WOD |
| **Overall** | **Optional** derived summary — prefer goal-specific progress |
| Future examples | body composition, running pace, strength, hydration, recovery, activity volume, mobility, environmental exposure |

Dashboard and directive surfaces select signals from:

- active goals and tasks  
- recent journal entries  
- available health data + freshness/confidence  
- selected dashboard view / user question  

**Backward compatibility:** existing scorers and `MVP-SCORE-*` tests remain; UI migrates under Goal Graph slices (`GG-*` / GL1).

**Transitional implementation detail:** code may still expose temporary labels **`readiness`** / **`soreness`**. Those are debt — not the permanent contract.

---

## 2. Local-first boundary

| Concern | Where it runs |
|---|---|
| LLM inference, normalization, scoring, reasoning, storage | **Local** (Apple Silicon M2 home host; Ollama + SQLite) |
| Fitbit (legacy fixture only) | **Not primary** — API deprecated for this product; keep fixtures only |
| Google Health / Takeout | **Primary metric sync** (ZIP today; live API when credentials exist) |
| Google Calendar | **External OAuth** (read-only); intended live calendar path |
| FITINDEX / body scale | **CSV export + screenshot/OCR + manual** — no scale OAuth |
| Open-Meteo weather / AQI | **Optional external** environmental connector; cached locally |
| Cloud LLM / cloud DB | **Not required**; not on the core path |
| Offline / degraded demo | Must work with **fixtures + manual entry** when Google Health/Calendar/weather/AQI are unavailable |

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
| Sleep / diet scorers | IT | Deterministic; diet blends Macro Pool when protein_g present |
| Readiness / soreness scorers | IL | **Transitional labels**; not canonical contract |
| Front-rack score | IT | Canonical scorer |
| Workout-preparation score | IT | Canonical scorer |
| Overall health/fitness score | IT | Blend of four canonical scores |
| SQLite log store | IT | Restart durability + schema_version proven (Slice 0) |
| Memory retrieval | IL | Dedup + exclude-self + today/history/conflicts wired; relevance still basic |
| Evidence provenance | IT | source / recorded_at / quality / extractor / content_hash |
| Safety disclaimer | IT | API + UI (MVP-DISCLAIMER-01); PHC-SAFETY-01 covered |
| WOD negotiation | IT | as_prescribed / scaled / substituted / deferred |
| Macro Pool ledger | IT | Wired into diet + canonical `macro_pool` |
| Dictation UI control | IL | Browser API; not E2E verified |
| Opt-in TTS | IL | Browser SpeechSynthesis when toggled |
| Google Health / Takeout | IT / F | **Primary** metric sync (ZIP + fixture); live Health API when secrets |
| Fitbit OAuth + metrics | F / NV | Legacy fixture only — **not primary**; no live-primary work |
| FITINDEX CSV / OCR / manual | IT / P | CSV + OCR drafts + manual review; **no scale OAuth** |
| Google Calendar (read-only) | F | Fixture events; live OAuth deferred |
| Chat + image + llava | IT / P | Unified composer (Ask + directive); image preview; click-to-pin page context; llava status honest |
| LLM metric-query tools | IT | Tools + parse_date |
| Inline charts | IT | Spec API + SVG renderer in overview |
| Alerts / custom thresholds | IT / P | Full API; overview panel (not full alert editor UI) |
| Goals + confirmation | IT / P | Full API; overview panel |
| Sync registry / staleness | IT | Registry + 24h stale + UI sync panel |
| Geolocation + weather/AQI | IT | Geo default-off; Open-Meteo live/offline/disabled |
| Grafana-style dashboard | P | Light overview (not full Grafana clone) |
| PWA / Tailscale remote | IT / docs | Manifest + Tailscale security doc |
| Automated tests | IT | **94** passed (`make os-test` / pytest) |
| Feature merge matrix | IT | `docs/FEATURE_MERGE_MATRIX.md` |

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

### 6.1 Google Health / Takeout (primary metric sync)

**Primary** wearable/metric path (see `docs/CONNECTORS.md`).

Ingest and normalize at least (via Takeout ZIP today; live Google Health API when credentials exist):

- Heart rate, HRV, resting heart rate, SpO2  
- Sleep duration / minutes asleep  
- Steps, distance, active minutes, calories  
- Body weight, body-fat %  
- Stress score, breathing rate  
- Activities  

Requirements: honest fixture/Takeout modes; live Health API only with real credentials (no mock auth backdoor); encrypted/local token storage when OAuth is added; graceful failure.

### 6.2 FITINDEX body composition (no scale OAuth)

Supported paths **only**:

1. CSV upload  
2. Screenshot / image OCR (local vision, e.g. Ollama `llava` when available)  
3. Manual text entry  
4. **User review and correction before save** (mandatory)

Scale / FITINDEX vendor OAuth is **never used** and must not be added.

### 6.3 Google Calendar (read-only OAuth — keep)

Ingest: event name, location, description, start/end.  
Write access: **forbidden**. Revocable OAuth; local cache only.  
This remains the **intended live calendar auth** path.

### 6.4 Fitbit (legacy fixture only — not primary)

Fitbit API is **not** the primary sync metric (refresh cadence unsuitable). Keep fixture / scaffold for compatibility tests only. Do not schedule live Fitbit OAuth as the main wearable path.

### 6.5 Other intake

- Generic natural-language health logging (`/api/intake` and chat tools)  
- Generic file drop  
- Manual text entry  
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
| Degradation | App remains usable with manual entry + fixtures if Google Health / Calendar / weather / AQI fail |

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

## 11. Goal Graph and task planning

Canonical detail: **`docs/GOAL_GRAPH.md`**.

Aegis maintains a living editable hierarchy:

`Vision → Goal → Project → Milestone → Task → Subtask → Evidence`

- Goals: outcomes / maintenance / habits / projects (vague wording preserved + editable structure).  
- Tasks: actions with inbox/today/upcoming/completed views.  
- Journal entries map to **goal contributions** (positive/negative/neutral/insufficient/conflicting) with evidence + confidence.  
- All meaningful mutations are **suggestions** until Approve / Edit / Reject / Defer.  
- Thin metric-target goals API remains as a compat layer until GL0–GL3 land.

Statuses (goals): `in_progress` | `completed` | `abandoned` | `paused`.  
Task statuses include `inbox` | `proposed` | `planned` | `in_progress` | `completed` | `skipped` | `canceled`.

Completion of Goal Graph requires the tested path:  
journal → evidence → suggestion → human approval → dashboard update.

---

## 12. Interface and deployment

### Desktop dashboard (progress workspace)

Daily directive (when requested), **goal-relevant signals** (not hardcoded four cards), alerts, source freshness, interactive long-term charts with goal bands, goal/task progress, evidence/history, sync controls, suggestion review.

### Conversation

Unified composer (journal + Ask); auto-growing textarea; optional Web Speech STT; image attachments; click-to-pin page sections as context; conversation thread inline; screen context via `AIContextProvider`.  
Searchable durable history: SQLite persist + `/api/chat/search` (S2 fixture).  
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
frontend/          PWA + progress workspace + unified composer
backend/
  intake/          NL + image → structured records
  connectors/      fitbit, calendar, fitindex, takeout, weather
  sync/            registry, background loop, staleness
  memory/          SQLite health DB + vector/evidence index
  signals/         pluggable providers (wrap scorers; GL1)
  scorers/         front_rack, sleep, diet, workout_prep, overall (compat)
  reasoner/        directive + tool-using chat + dual safety modes
  alerts/          thresholds + history
  goals/           Goal Graph + HITL suggestions (GL0+)
  charts/          validated chart specs + goal overlays
  intelligence/    typed screen context
  obs/             local tracing
```

External connectors are adapters; core reasoning never hard-depends on them.

---

## 14. Implementation order (next)

See **`docs/IMPLEMENTATION_PLAN.md`** + **`docs/CONNECTORS.md`** for the authoritative ordered slices and connector policy.

1. Foundation slices 0–11 + feature aggregate — **done**  
2. S1 background sync + unified composer — **done**  
3. GL0–GL5 Goal Graph + GG-E2E/SAFETY fixtures + S2 chat persist — **done (fixture)**  
4. **S8** — Expand Playwright beyond smoke to full Goal Graph §12 browser path  
5. **S5a** — FITINDEX CSV + OCR confirm UX (no scale OAuth)  
6. **S5b / S5** — Google Health / Takeout UX; live Health API when secrets (**not Fitbit**)  
7. **S6** — Live Google Calendar OAuth when secrets; geo consent already present  
8. **GL6 / S7** — Tailscale Funnel + PWA install operator acceptance  

**Dev command:** `make os-dev` (alias: `make dev`).

---

## 15. Testing doctrine

| Layer | Proves |
|---|---|
| Unit tests | Function behavior |
| Integration tests | Connector/DB wiring with fixtures |
| E2E / acceptance | UI + API + persistence user journeys |
| Success criteria artifacts | DoD evidence only when `verify` passes |

UI presence ≠ backend implementation ≠ live integration ≠ E2E verification.

Requirements that still **lack full live/E2E coverage** (non-exhaustive): Google Health live API, Google Calendar OAuth security, FITINDEX confirm UX depth, Playwright Goal Graph §12, geolocation privacy browser path, Tailscale accept, chart/alert polish — see `PHC-*` / `GG-*` rows in `success_criteria.yaml` and `docs/CONNECTORS.md`.
