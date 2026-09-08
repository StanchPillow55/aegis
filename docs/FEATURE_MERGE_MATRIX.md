# Aegis Feature Merge Matrix

**Target (canonical):** `/workspace` — `github.com/StanchPillow55/aegis`  
**Older prototype (read-only):** `origin/legacy-aegis` extracted to `/workspace/legacy-aegis` (no `.git`; do not modify remote `legacy-aegis`)  
**Legacy tip:** `9a4e50ec61abc3c1c5a93894695c536c2cd1bed2`  
**Matrix date:** 2026-09-08  
**Merge type:** Semantic feature aggregation (not a Git merge)

## Provenance of older tree

| Item | Detail |
|---|---|
| Remote branch | `https://github.com/StanchPillow55/aegis/tree/legacy-aegis` |
| Local mirror | `/workspace/legacy-aegis` via `git archive origin/legacy-aegis` |
| Primary code | `legacy-aegis/src/{backend,frontend}` |
| Nested hackathon | `legacy-aegis/legacy/` (already lineage of canonical; SKIP re-port) |
| Specs | `legacy-aegis/.kiro/specs/`, `docs/IMPLEMENTATION_PLAN.md` |

### Status codes

| Code | Meaning |
|---|---|
| **I** | Implemented (real logic + tests or manual validation) |
| **F** | Fixture / offline mode (deterministic; not live OAuth/API success) |
| **P** | Partial (backend or UI only; missing half) |
| **S** | Stub / contract only |
| **M** | Missing |
| **D** | Deferred intentionally |
| **V** | Verified present in legacy tree (file-inspected) |

---

## Matrix

| Feature | Source | Target now | Older | Compatible | Action | Dependencies | Evidence | Final |
|---|---|---|---|---|---|---|---|---|
| Canonical health schema | both | I | V | Y | Keep target schema | — | `backend/health/schema.py` | **Keep** |
| Provenance + SQLite + dedup + today_wins | target | I | V (partial) | Y | Keep target | — | Slice 0–1 tests | **Keep** |
| Safety disclaimer | both | I | V | Y | Keep | — | PHC-SAFETY | **Keep** |
| Safety language guardrails | older | I | V | Y | Ported `apply_guardrails` into chat | — | `backend/safety/`, `test_legacy_ports` | **Done** |
| Source registry + 24h staleness | target | I | V (scheduler) | Y | Keep registry; skip APScheduler boot-req | — | PHC-SYNC/STALE | **Keep** |
| Manual NL intake → directive | both | I | V | Y | Keep | — | `/api/directive` | **Keep** |
| Fitbit fixture metrics | target | F | — | Y | Keep | — | PHC-FITBIT | **Keep F** |
| Fitbit live OAuth + API | older | P | V | Y | Scaffold status/auth/callback; live only with secrets | `FITBIT_*` | `/api/fitbit/*`, `fitbit_oauth.py` | **Scaffold Done** |
| FITINDEX CSV + manual review | target | I | V | Y | Keep | — | PHC-FITINDEX | **Keep** |
| FITINDEX screenshot OCR | older | I | V | Y | Ported llava OCR → draft (confirm required) | Ollama llava | `/api/fitindex/ocr` | **Done** |
| FITINDEX NL text extract | older | I | V | Y | Heuristic draft path (no Claude required) | — | `/api/fitindex/text` | **Done** |
| Google Takeout CSV | target | I | V | Y | Keep | — | takeout CSV | **Keep** |
| Google Takeout JSON Data Points | older | I | V | Y | Ported into takeout ZIP ingest | — | `test_takeout_json` | **Done** |
| Calendar fixture | target | F | — | Y | Keep | — | PHC-CALENDAR | **Keep F** |
| Calendar live Google OAuth | older | M/S | V | Y | Deferred until Google secrets; no fake connected | secrets | — | **Deferred** |
| Calendar lifestyle signals | older | I | V | Y | Ported early/late/busy/travel derivation | optional geopy | `/api/calendar/signals` | **Done** |
| Geolocation privacy default-off | both | I | V | Y | Keep; never cloud LLM | — | `/api/geo/status` | **Keep** |
| Open-Meteo weather/AQI | both | I | V (fake fallback CONFLICT) | Y | Canonical honest modes win; live verified | network | `mode=live` smoke | **Done** |
| Front-rack/Sleep/Diet/WP/Overall | target | I | — | Y | Keep as **pluggable signal providers**; dashboard migrates to Goal Graph | — | MVP-SCORE + GG-SIGNAL | **Migrate** |
| Goal Graph hierarchy + HITL | plan | M | — | Y | New major layer (`docs/GOAL_GRAPH.md`) | GL0–GL5 | GG-* | **Planned** |
| Hydration + performance factors | older | I | V | Y | Ported as `scores.factors.*` (not top-level) | optional intake fields | `test_legacy_ports` | **Done** |
| Macro Pool | target | I | — | Y | Keep | — | MVP-MACRO | **Keep** |
| WOD negotiation | target | I | V (partial) | Y | Keep | — | MVP-WOD | **Keep** |
| Goals + confirm (metric-target) | both | I | V | Y | Compat until Goal Graph replaces UI contract | — | PHC-GOALS | **Compat** |
| Alerts defaults/custom | both | I | V | Y | Keep API; light UI | — | PHC-ALERTS | **Keep** |
| LLM tools + dateparser | both | I | V | Y | Keep + body_comp/calendar/correlate/trend | — | tools | **Done** |
| Patterns / correlations / trends | older | I | V | Y | Ported SQL-free metric trends + Pearson | metrics store | `/api/patterns/*` | **Done** |
| Chroma semantic search | older | M | V | N* | Skip — SQLite memory is DoD | — | — | **D** |
| Chart specs + SVG render | target | I | V (Recharts) | Y | Keep SVG; skip Vite SPA; bands via GL4 | — | charts | **Keep** |
| Text chat + sessions | older→target | I | V | Y | Unified composer + SQLite persist/search (S2) | — | `/api/chat` | **Done** |
| Image attach/preview | target | P | V | Y | Unified composer (no chat dock) | — | composer | **Partial** |
| Vision / llava status + OCR | both | I | V | Y | Status + FITINDEX OCR when model present | Ollama | vision + ocr | **Done** |
| Rich AIContext / system context | older | I | V | Y | Ported vitals/alerts/goals/stale/calendar | — | `/api/context/screen` | **Done** |
| Sync/settings/overview UI | target | I light | V (Vite SPA) | Y | Keep static UI; skip SPA rewrite | — | frontend | **Keep light** |
| PWA | both | P | V | Y | Manifest; SW/icons later | — | PHC-PWA | **Partial** |
| Multi-user X-User-ID | older | M | V | N | Skip for local single-user | — | — | **D** |
| Nested `legacy/` Redis/Deepgram | older | Out | V | N | Quarantine | — | — | **D** |
| Fake OAuth / silent fake weather | older risk | Forbidden | V (weather fallback) | N | Never port | — | — | **Forbid** |

\*Incompatible with current local-first SQLite-memory DoD unless product reverses.

---

## Summary (post legacy re-audit)

| Bucket | Count (approx) |
|---|---|
| Keep / already done | ~25 |
| Ported this pass from legacy | ~12 |
| Deferred (creds / SPA / Chroma / multi-user) | ~6 |
| Forbidden | fake OAuth, silent fake weather |

## Validation

- Local: `make os-test` — **103** passed  
- Live Open-Meteo: `mode=live` after egress approval  
- Branch: `cursor/feature-merge-aggregate-766c` / PR #29  
