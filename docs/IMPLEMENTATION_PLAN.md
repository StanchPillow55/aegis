# Aegis Implementation Plan — Goal Graph era (QA + product revision)

**Canonical branch tip:** `cursor/s1-background-sync-3696` · [PR #31](https://github.com/StanchPillow55/aegis/pull/31) (on #29)  
**DoD:** `success_criteria.yaml` · Maturity: `docs/SC_MATURITY.md` · Spec: `docs/PRODUCT_SPEC.md` · Goal Graph: `docs/GOAL_GRAPH.md` · Connectors: `docs/CONNECTORS.md` · Matrix: `docs/FEATURE_MERGE_MATRIX.md`  
**Date:** 2026-09-08 (Goal Graph layer + connector policy reframed)  

---

## 0. Where we are (honest)

Aegis is a **local-first** daily training-decision / personal health copilot (FastAPI + SQLite + static frontend). Foundation through PR **#29** is CI-green. On this tip:

| Capability | Status |
|---|---|
| Schema / evidence / directive loop | Working |
| Sync registry + **required background sync (S1)** | Fixture-verified |
| Fixture connectors (Calendar / Takeout / Fitbit-legacy / FITINDEX CSV+OCR) | Fixture-verified |
| Canonical scorers (FR/Sleep/Diet/WP/Overall) | Working as **compat signal layer** |
| Goal Graph GL0–GL5 + GG-E2E/SAFETY fixtures | Fixture-verified |
| Unified expanding composer + click-to-pin | Working |
| Chat SQLite persist/search (S2) | Fixture-verified |
| Dual safety output modes | Fixture-verified (API + UI labels) |
| PWA SW + icon | Fixture-verified; install accept operator-owned |
| Playwright Goal Graph §12 | Opt-in (`AEGIS_PLAYWRIGHT=1`) — **done** |
| Recovery / running_pace / body / activity signals | Computed (no longer stubs) |
| Sync labels | Takeout **primary**; Fitbit **legacy**; FITINDEX no scale OAuth |
| Local SQLite backup/restore | API + Settings UI |
| Live Google Calendar / Google Health OAuth | Open / blocked-on-secrets |
| Fitbit live API | **Out of primary scope** — legacy fixture only |

**Connector policy (non-negotiable):** see **`docs/CONNECTORS.md`**.

| Connector | Policy |
|---|---|
| **Google Health / Takeout** | **Primary metric sync** |
| **Google Calendar OAuth** | **Keep** — intended live calendar auth |
| **FITINDEX / scale** | **CSV + image OCR + manual only** — scale OAuth never used; do not add |
| **Fitbit API** | **Not primary** — deprecated for this product; fixture scaffold only |

Treat `pass: true` as automated verify green, not product-complete. See `docs/SC_MATURITY.md`.

---

## 1. Completed progress (stacked PRs)

| Slice | PR | Result |
|---|---|---|
| OS local foundation + text UI | #22 | CI green |
| MVP / PRODUCT_SPEC expansion | #23 | CI green |
| 0 Schema / evidence / disclaimer | #24 | CI green |
| 1 Source registry + sync | #25 | CI green |
| 2–5 Metrics ingest + fixture connectors | #26 | CI green |
| 6–11 Scores, WOD, alerts, goals, tools, charts, PWA docs | #27 | CI green |
| BUG-LOCALHOST-01 | #28 | CI green |
| Feature aggregate + legacy residual ports | #29 | CI green |
| **S1** Required background sync | #31 | CI green |
| Unified composer (journal + Ask + pin context) | #31 | CI green |
| **GL0–GL5** Goal Graph core + signals + HITL + UI + progress + context | #31 | Fixture-verified |
| **S2** Chat persist/search | #31 | Fixture-verified |
| **GG-E2E-01 / GG-SAFETY-01** API fixture path | #31 | Fixture-verified |

---

## 2. Product-model migration (critical)

### Before (current contract debt)
Dashboard + directive assume permanent top-level: Front-rack / Sleep / Diet / Workout-prep / Overall.

### After (Goal Graph contract)
1. Those scorers remain as **pluggable signal providers** (backward compatible).  
2. Dashboard + directive surface **signals relevant to active goals + recent entries**.  
3. Universal **overall** score is **optional**.  
4. Existing `MVP-SCORE-01` stays green via compat providers; `GG-*` criteria own the dynamic contract.

Details: **`docs/GOAL_GRAPH.md`**.

### Safety dual outputs
1. **Health analysis** (chat) — observational / non-prescriptive.  
2. **Training planning** (directive) — labeled non-medical decision support + disclaimer + confirm material plan changes.

---

## 3. Priority backlog (current)

### Done (do not restart)
GL0 · GL1 · GL2 · GL3 · GL4 · GL5 · S1 · S2 · GG-E2E fixture · GG-SAFETY · dual safety labels · geo consent UI · PWA SW/icon smoke · **S8 Playwright §12 browser** · **S5a FITINDEX confirm UX** · **S5b Takeout preview/provenance** · **S9** PDF-gap polish (computed signals + sync label honesty + backup/restore)

### P0 — Docs / merge hygiene
1. Keep connector policy honest (`docs/CONNECTORS.md`).  
2. Merge hygiene for #22–#31 when ready.

### P1 — Next implementation (no secrets required)

| ID | Work | Notes |
|---|---|---|
| Overview UX | Soften raw JSON panels on Overview (operator polish) | Optional |

### P1 — When Google secrets available

| ID | Work | Notes |
|---|---|---|
| **S6** | Live **Google Calendar** read-only OAuth | Calendar Google auth remains the intended live path |
| **S5** | Live **Google Health API** (beyond Takeout ZIP) | **Primary** wearable/metric sync — **not Fitbit** |
| **PHC-OAUTH-01** live | Secure local token store for Google tokens | No Fitbit-primary; no scale OAuth |

### P2 — Remote / operator accept

| ID | Work | Notes |
|---|---|---|
| **GL6 / S7** | Mobile goal-task polish + Tailscale remote parity | SW/icons fixture done; mesh accept operator-owned |

### Cancelled / out of scope (do not schedule)

| Former idea | Disposition |
|---|---|
| Fitbit live OAuth as primary sync (old S5) | **Cancelled as primary** — keep legacy fixture only (`docs/CONNECTORS.md`) |
| FITINDEX / body-scale vendor OAuth | **Never used — do not implement** |
| Fake OAuth success / silent fake weather | **Forbidden** |

### Do not do
- Silent goal/task mutations  
- Fake OAuth / silent fake weather  
- Reintroduce Fitbit API as primary metric sync  
- Add FITINDEX/scale OAuth  
- Delete score implementations (migrate to providers)  
- Mark Goal Graph product-complete from fixtures alone (Playwright §12 still open)  
- Boot-required Redis/Deepgram/Anthropic/Browserbase  
- Modify remote `legacy-aegis`  

---

## 4. Goal Graph slices (exit criteria)

| Slice | Scope | Exit criteria |
|---|---|---|
| **GL0** | Schema: goals, tasks, revisions, evidence, contributions, suggestions, audit | **DONE fixture** |
| **GL1** | Pluggable signals; overall optional | **DONE fixture** |
| **GL2** | Journal contributions + HITL suggestions | **DONE fixture** |
| **GL3** | Goal tree / task views / editor / suggestion panel | **DONE fixture** |
| **GL4** | Progress horizons / bands / explain / chart→task | **DONE fixture** |
| **GL5** | Typed screen context + read vs mutate-preview tools | **DONE fixture** |
| **GL6** | Responsive + PWA + Tailscale parity | Operator accept still open |
| **GG-E2E** | §12 path | **DONE** API fixture + Playwright browser (`AEGIS_PLAYWRIGHT=1`) |

### Required E2E story (fixture → then Playwright)
1. Create goal from conversation  
2. Submit journal entry  
3. Retrieve prior evidence  
4. Propose goal contribution  
5. Suggest task  
6. Edit + approve  
7. Dashboard + history update  
8. Screen-aware chat about updated dashboard  

**API fixture path:** `artifacts/gg-e2e-fixture.txt`.  
**Browser path:** `artifacts/s8-playwright-gg-e2e.txt` (`AEGIS_PLAYWRIGHT=1`).

---

## 5. Operational slices (connector-aware)

| Slice | Scope | Status / note |
|---|---|---|
| **S1** | Background sync | **DONE** |
| **S2** | Chat SQLite persist + search | **DONE fixture** |
| **S3** | Thin NL goals (old) | **Superseded by GL0–GL3** |
| **S4** | Interactive charts | Absorbed into **GL4** |
| **S5** | **Google Health / Takeout** primary metrics | Takeout preview+confirm UX done; live Health API when secrets — **not Fitbit** |
| **S5a** | FITINDEX CSV + OCR confirm UX | **DONE** — no scale OAuth |
| **S5b** | Takeout preview + provenance | **DONE** |
| **S6** | Geo + **Google Calendar** live OAuth | Geo consent UI present; Calendar OAuth when secrets |
| **S7** | PWA + Tailscale accept | SW+icons fixture; mesh operator-owned |
| **S8** | Playwright + offline/backup | **DONE** §12 browser + backup/restore |
| **S9** | PDF-tested gap polish | Computed recovery/pace/body/activity · sync labels · backup |

**Recommended order now:**  
**(secrets) S6 Calendar + S5 Google Health API → GL6/S7 remote accept · optional Overview JSON polish**

### Operator PDF check (2026-09-07)
Manual UI exercise confirmed: composer → directive, goal tree + HITL suggestions, Settings connector policy, Takeout/FITINDEX panels. Gaps closed in S9: stub recovery/pace signals, Takeout “fallback” sync label, missing backup.

---

## 6. Connector / OAuth checklist

Canonical: **`docs/CONNECTORS.md`**.

| Connector | Policy | Next task |
|---|---|---|
| Google Health / Takeout | **Primary** metric sync | S5 / S5b |
| Google Calendar OAuth | **Keep** live path | S6 |
| FITINDEX / scale | CSV + image OCR only | S5a — never scale OAuth |
| Fitbit API | Legacy fixture only | No live-primary work |

Do not fake OAuth. Goal Graph may use fixtures / Takeout / manual until Google Health live credentials exist.

---

## 7. Commands

```bash
python3 -m pip install -r requirements.txt
python3 scripts/validate_product_docs.py
python3 scripts/validate_success_criteria.py
make os-test
make os-dev          # SAME machine as browser → http://127.0.0.1:8000/
make os-health

# Optional browser smoke (S8)
AEGIS_PLAYWRIGHT=1 AEGIS_BASE_URL=http://127.0.0.1:8000 \
  python3 -m pytest tests/test_remaining_polish.py::test_s8_playwright_goal_graph_smoke -q
```

Localhost trap: `docs/bugs/BUG-LOCALHOST-01.md`.

---

## 8. Key paths

| Area | Path |
|---|---|
| Goal Graph spec | `docs/GOAL_GRAPH.md` |
| Connector policy | `docs/CONNECTORS.md` |
| App | `backend/main.py` |
| Goals / progress / tools | `backend/goals/` |
| Signals / scorers | `backend/signals/`, `backend/scorers/` |
| Sync | `backend/sync/` |
| Chat / context | `backend/chat/`, `backend/context/`, `backend/intelligence/context.py` |
| Takeout / FITINDEX / Calendar | `backend/connectors/` |
| Frontend | `frontend/` |
| Maturity | `docs/SC_MATURITY.md` |
