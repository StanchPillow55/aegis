# Aegis Implementation Plan — Goal Graph era (QA + product revision)

**Canonical branch tip:** `cursor/s1-background-sync-3696` · [PR #31](https://github.com/StanchPillow55/aegis/pull/31) (on #29)  
**DoD:** `success_criteria.yaml` · Maturity: `docs/SC_MATURITY.md` · Spec: `docs/PRODUCT_SPEC.md` · Goal Graph: `docs/GOAL_GRAPH.md` · Matrix: `docs/FEATURE_MERGE_MATRIX.md`  
**Date:** 2026-09-08 (Goal Graph + context-aware planning layer added; slices reordered)  

---

## 0. Where we are (honest)

Aegis is a **local-first** daily training-decision / personal health copilot (FastAPI + SQLite + static frontend). Foundation through PR **#29** is CI-green. On this tip:

| Capability | Status |
|---|---|
| Schema / evidence / directive loop | Working |
| Sync registry + **required background sync (S1)** | Fixture-verified |
| Fixture connectors (Fitbit/Calendar/Takeout) | Fixture-verified |
| Canonical scorers (FR/Sleep/Diet/WP/Overall) | Working as **compat signal layer** |
| Simple goals API (metric-target + confirm) | Thin — **superseded by Goal Graph plan** |
| Unified expanding composer + click-to-pin | Working (no floating chat dock) |
| Live OAuth / Playwright E2E / PWA install | Open |

**Next major product layer:** **Goal Graph and Context-Aware Planning Layer** (`docs/GOAL_GRAPH.md`).  
Fixed scores become **optional, goal-relevant signals** — not permanent top-level dashboard categories.

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

---

## 2. Product-model migration (critical)

### Before (current contract debt)
Dashboard + directive assume permanent top-level: Front-rack / Sleep / Diet / Workout-prep / Overall.

### After (Goal Graph contract)
1. Those scorers remain as **pluggable signal providers** (backward compatible).  
2. Dashboard + directive surface **signals relevant to active goals + recent entries**.  
3. Universal **overall** score is **optional**.  
4. Existing `MVP-SCORE-01` stays green via compat providers; new `GG-*` criteria own the dynamic contract.

Example journal: *“Ate beef and rice, run was good, averaged 10:30 for 3 miles.”*

| Goal | Contribution |
|---|---|
| Conditioning | Positive progress |
| Nutrition | Protein/meal recorded (partial) |
| Running task | Suggest pace tracking |
| Recovery | Insufficient evidence |
| Body composition | No direct update |

Details: **`docs/GOAL_GRAPH.md`**.

### Safety dual outputs (unchanged)
1. **Health analysis** — observational.  
2. **Training planning (directive)** — labeled non-medical decision support + disclaimer + confirm material plan changes.

---

## 3. Priority backlog (reordered)

### P0 — Docs / merge hygiene
1. Keep Goal Graph docs + SC rows honest (`planned` until path tested).  
2. Merge hygiene for #22–#31 when ready.

### P1 — Goal Graph core (start here)
| ID | Work |
|---|---|
| **GL0** | Goal/task hierarchy schema, revisions, evidence links, suggestions, audit |
| **GL1** | Dynamic signal abstraction (preserve scorers as providers) |
| **GL2** | Journal contribution engine (RAG + classify + suggestions + HITL) |
| **GL3** | Goal/task UI (tree, inbox, editor, suggestion review) |

### P1 — Supporting operational (interleave as needed)
| ID | Work | Notes |
|---|---|---|
| **S2** | Chat SQLite persist + search | Feeds GL5; still required |
| **S5** | Fitbit live metrics + OAuth security | Evidence richness for Goal Graph |
| Dual safety labels in reasoner/UI | Enforce analysis vs planning |

### P2 — Progress surfaces + connectors
| ID | Work |
|---|---|
| **GL4** | Long-term progress dashboards (horizons, bands, explain/create-task) |
| **GL5** | Context-aware chat (typed screen context, read vs mutate tools) |
| **S4** | Interactive chart behaviors (absorbed into GL4 where overlapping) |
| Calendar live OAuth | S6 partial |
| Geo privacy UI | S6 partial |
| FITINDEX confirm UI | |

### P2/P3 — Remote + verification
| ID | Work |
|---|---|
| **GL6** | Mobile/PWA goal-task views + Tailscale remote parity |
| **S7** | PWA SW/icons + authenticated remote acceptance |
| **S8** | Playwright E2E incl. Goal Graph path |
| Offline / backup / M2 perf | |

### Do not do
- Silent goal/task mutations  
- Fake OAuth / silent fake weather  
- Delete score implementations (migrate to providers)  
- Mark Goal Graph complete from stubs/placeholders  
- Boot-required Redis/Deepgram/Anthropic/Browserbase  
- Modify remote `legacy-aegis`  

---

## 4. Goal Graph slices (exit criteria)

| Slice | Scope | Exit criteria |
|---|---|---|
| **GL0** | Model + SQLite schema: goals hierarchy, tasks, revisions, evidence links, journal contributions, suggestions, approval state, audit | **DONE fixture** (`artifacts/gl0-goal-graph-schema.txt`) — UI/E2E still open |
| **GL1** | Signal provider interface; wrap FR/Sleep/Diet/WP/Overall; dynamic selection API; UI no longer *requires* four fixed cards | **DONE fixture** (`artifacts/gl1-signals.txt`) — compat `score_canonical` preserved |
| **GL2** | Journal contribution engine: RAG, map to goals, classify effect, task suggestions, evidence/assumptions/confidence, approve/edit/reject/defer | **DONE fixture** (`artifacts/gl2-contributions.txt`) — UI suggestion panel still open (GL3) |
| **GL3** | Goal tree + task inbox + Today/Upcoming/Completed + editor + suggestion panel + decompose/rewrite/archive | **DONE fixture** (`artifacts/gl3-goal-ui.txt`) — Playwright E2E still open |
| **GL4** | Progress workspace: horizons, trends, goal bands, milestones, annotations, missing/stale, explain + create-task-from-chart | Fixture charts + goal overlays; explain action returns evidence-bound text |
| **GL5** | Typed screen context expansion; read-only tools; mutation preview tools; confirm mutations; searchable chat history; inline charts | Context regression tests; no raw HTML to LLM |
| **GL6** | Responsive goal/task + suggestion review; PWA; Tailscale remote same behavior | Checklist artifact; maturity not `verified` until operator accept |

### Required E2E story (fixture → then Playwright)
1. Create goal from conversation  
2. Submit journal entry  
3. Retrieve prior evidence  
4. Propose goal contribution  
5. Suggest task  
6. Edit + approve  
7. Dashboard + history update  
8. Screen-aware chat about updated dashboard  

**Completion requires this path.** Models/UI placeholders alone are insufficient.

---

## 5. Operational slices (retained, reordered relative to Goal Graph)

| Slice | Scope | Status / note |
|---|---|---|
| **S1** | Background sync | **DONE** |
| **S2** | Chat SQLite persist + search | After GL0 or parallel with GL5 |
| **S3** | Thin NL goals/alerts (old) | **Superseded by GL0–GL3**; keep alerts work |
| **S4** | Interactive charts | Prefer implement inside **GL4** |
| **S5** | Fitbit full metrics + OAuth security | After GL2 or when secrets available |
| **S6** | Geo UI + Calendar live | After GL4 or with secrets |
| **S7** | PWA + Tailscale accept | Align with **GL6** |
| **S8** | Playwright + offline/backup | Include Goal Graph E2E |

**Recommended start (no secrets):**  
**GL0 (done fixture) → GL1 → GL2 → GL3 → S2 → GL4 → GL5 → S8(partial)**  
**With Fitbit secrets:** insert **S5** after GL2.  
**Remote polish:** **GL6 / S7**.

---

## 6. Fitbit / OAuth checklist (still required)

Full metric list + OAuth security checklist unchanged from QA revision (see prior §4.2). Live path remains `blocked-on-secrets` until clients exist. Goal Graph uses fixture metrics until then.

---

## 7. Commands

```bash
python3 -m pip install -r requirements.txt
python3 scripts/validate_product_docs.py
python3 scripts/validate_success_criteria.py
make os-test
make os-dev          # SAME machine as browser → http://127.0.0.1:8000/
make os-health
```

Localhost trap: `docs/bugs/BUG-LOCALHOST-01.md`.

---

## 8. Key paths

| Area | Path |
|---|---|
| Goal Graph spec | `docs/GOAL_GRAPH.md` |
| App | `backend/main.py` |
| Goals (compat → graph) | `backend/goals/` |
| Signals / scorers | `backend/scorers/`, future `backend/signals/` |
| Sync | `backend/sync/` |
| Chat / context | `backend/chat/`, `backend/intelligence/context.py` |
| Frontend composer | `frontend/` |
| Maturity | `docs/SC_MATURITY.md` |
