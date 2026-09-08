# AGENT_HANDOFF — aegis

**Read first (in order):**
1. `docs/PRODUCT_SPEC.md` — product + architecture contract  
2. `docs/GOAL_GRAPH.md` — Goal Graph + context-aware planning (next major layer)  
3. `docs/IMPLEMENTATION_PLAN.md` — ordered slices (GL0–GL6 + S*)  
4. `docs/SC_MATURITY.md` — what `pass: true` actually means  
5. `docs/FEATURE_MERGE_MATRIX.md` — legacy vs canonical feature status  
6. `success_criteria.yaml` — DoD automation (`GG-*` planned; `MVP-*`/`PHC-*` foundation)  
7. `CLAUDE.md` — build contract  
8. `docs/bugs/BUG-LOCALHOST-01.md` — if UI “won’t open” from a Cloud Agent

---

## TL;DR for a new agent

Branch tip: `cursor/s1-background-sync-3696` ([PR #31](https://github.com/StanchPillow55/aegis/pull/31)).

**Foundation + S1 + unified composer are shipped.** Next major product layer is the **Goal Graph and Context-Aware Planning Layer** — not “add Google Tasks,” and not more fixed score cards.

**Product decision:** Front-rack / Sleep / Diet / Workout preparation remain **analyzers**. Dashboard + directive surface **goal-relevant signals**. Overall score is optional.

**Do not** treat SC `pass: true` as product complete. Use `docs/SC_MATURITY.md`.  
**Do not** mark Goal Graph done from schema/UI placeholders — need journal → evidence → suggestion → approval → dashboard E2E.  
**Do not** modify remote `legacy-aegis`. **Do not** fake OAuth or silent mutations.

---

## Progress (stacked PRs — CI green)

| Slice | PR | Result |
|---|---|---|
| OS → feature aggregate | #22–#29 | CI green |
| S1 background sync + unified composer | #31 | CI green |

### Verification (foundation)

| Check | Result |
|---|---|
| Tests | **114+** pytest (`make os-test`) |
| SC automation | Existing rows `pass: true` = verify scripts green — see maturity map |
| Open-Meteo | Live when egress allowed |
| Demos | `make mvp-demo` / `make os-demo` |

---

## What works today (vs Goal Graph)

### Existing working score / directive behavior
- Text/journal → extract → evidence (today_wins) → directive  
- Scorers: Front-rack / Sleep / Diet / Workout-prep / Overall (+ Macro Pool, WOD)  
- Dual safety modes still to enforce more clearly in copy (analysis vs planning)  
- Background sync; fixture connectors; unified composer + pin context  

### Still thin / planned
| Layer | Status |
|---|---|
| Dynamic signal migration (GL1) | Planned — preserve scorers as providers |
| Goal/task infrastructure (GL0) | Planned — supersedes thin metric-target goals |
| Journal contribution + HITL (GL2–GL3) | Planned |
| Progress dashboards (GL4) | Planned |
| Context-aware chat depth (GL5) + S2 persist | Planned |
| UI work for goal tree / suggestions | Planned |
| E2E verification (S8 + Goal Graph story) | Planned |
| OAuth + remote access (S5–S7 / GL6) | Open / blocked-on-secrets |

---

## Known limitations

- Fixed four-score dashboard still present in UI (compat); not yet dynamic.  
- Goals API is metric-target only — not full Goal Graph hierarchy.  
- Chat sessions are in-memory (S2 pending).  
- Live Fitbit/Calendar OAuth incomplete.  
- No Playwright Goal Graph E2E yet.  
- `pass: true` ≠ live/E2E complete.

---

## Next implementation order

1. **GL0** — Goal/task schema, revisions, suggestions, audit (`GG-SCHEMA-01`) — **fixture-verified**  
2. **GL1** — Pluggable signals; stop treating FR/Sleep/Diet/WP as mandatory cards (`GG-SIGNAL-01`) — **fixture-verified**  
3. **GL2** — Journal contribution engine + HITL (`GG-CONTRIB-01`, `GG-SUGGEST-01`)  
4. **GL3** — Goal/task UI + suggestion review (`GG-UI-01`)  
5. **S2** — Chat SQLite persist/search (supports GL5)  
6. **GL4** — Progress dashboards / bands / explain (`GG-PROGRESS-01`)  
7. **GL5** — Typed screen context + read/mutate tools (`GG-CONTEXT-01`)  
8. **S5/S6** — Fitbit/Calendar/geo when secrets  
9. **GL6/S7/S8** — Remote/PWA + Playwright Goal Graph path  

Details: `docs/IMPLEMENTATION_PLAN.md` · models: `docs/GOAL_GRAPH.md`.

Historical note: **Slice 0** (schema/evidence) is already done; do not restart it.

---

## Safety: two output modes (enforce)

1. **Health analysis** — observational / non-prescriptive.  
2. **Training planning (directive)** — labeled non-medical decision support; disclaimer; confirm material plan changes.

Goal suggestions are a third HITL surface — never silent writes.

---

## Localhost / browser

`make os-dev` → `http://127.0.0.1:8000/` on the **same host**.  
Cloud Agent localhost ≠ laptop localhost. See `docs/bugs/BUG-LOCALHOST-01.md`.

---

## Legacy prototype

| Item | Detail |
|---|---|
| Remote | `origin/legacy-aegis` — **do not push/modify** |
| Local | `/workspace/legacy-aegis` via `git archive` (gitignored) |

---

## Rules (non-negotiable)

1. Mark complete in prose only when `docs/SC_MATURITY.md` says so.  
2. Preserve intake/directive behavior while migrating signals.  
3. Never silent goal/task mutations.  
4. Never fake OAuth / fake weather.  
5. Fixtures OK if labeled.  
6. UI ≠ backend ≠ live ≠ E2E.  

---

## Quickstart

```bash
python3 -m pip install -r requirements.txt
python3 scripts/validate_product_docs.py
make os-test
make os-dev
make os-health
```
