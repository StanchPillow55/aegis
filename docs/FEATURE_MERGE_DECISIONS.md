# Feature Merge Decisions

**Date:** 2026-09-08  
**Target:** `/workspace` (`cursor/s1-background-sync-3696` on `cursor/feature-merge-aggregate-766c`)  
**Older prototype:** `origin/legacy-aegis` → `/workspace/legacy-aegis` (read-only archive; remote branch untouched)  
**Connector policy:** `docs/CONNECTORS.md` (authoritative)

---

## 1. Architectural decisions

| Decision | Choice | Rationale |
|---|---|---|
| Canonical architecture | Current FastAPI + SQLite + static frontend | Passing tests; product local-first |
| Older tree role | Read-only feature source at `/workspace/legacy-aegis` | Extracted via `git archive`; never push to `legacy-aegis` |
| Merge style | Semantic port | Layouts differ (`src/backend` vs `backend`) |
| Score contract | Keep Front-rack/Sleep/Diet/WP/Overall | Hydration/performance ported as **factors** only; dashboard migrating to Goal Graph signals |
| Chroma | Skip | SQLite memory is DoD |
| Vite/Recharts SPA | Skip wholesale rewrite | Enhance static UI; single `make os-dev` |
| Fake weather / fake OAuth | Forbidden | Legacy silent 22.5°C fallback not ported |
| **Primary metric sync** | **Google Health / Takeout** | Operator decision 2026-09-08 — not Fitbit |
| **Calendar auth** | **Google Calendar OAuth (keep)** | Intended live calendar path |
| **FITINDEX / scale** | **CSV + image OCR + manual only** | Scale OAuth never used; do not add |
| **Fitbit API** | **Not primary** | Refresh cadence unsuitable; legacy fixture only |

---

## 2. Conflicts and resolutions

| Conflict | Resolution |
|---|---|
| Legacy 6-dim scores vs canonical 5-dim | Canonical wins; hydration/performance → `scores.factors` |
| Legacy Open-Meteo hardcoded fallback | Canonical `live\|offline\|disabled` labeling |
| Legacy “Live Sync” UI badge | Not ported; sync panel shows honest states |
| Calendar OAuth token field mismatch in legacy | Do not port buggy Google token store blindly; signals + fixture first; live OAuth when secrets |
| Fitbit Fernet demo seed / “authenticated” UX | Prefer `AEGIS_TOKEN_KEY` / data-dir-derived key; no fake authenticated; Fitbit not primary |
| Dual-process Makefile (backend+frontend) | Keep single `make os-dev` (+ `make dev` alias) |
| Old plan “S5 = Fitbit live” | **Cancelled as primary** — S5 / S5b = Google Health / Takeout |

---

## 3. Migrations performed (legacy re-audit pass)

1. Fetched `origin/legacy-aegis` → `/workspace/legacy-aegis` (gitignored).  
2. Re-audited matrix with verified **V** older columns.  
3. Ported: guardrails, Fitbit OAuth **scaffold** (legacy only), FITINDEX OCR/text drafts, Takeout JSON, calendar signals, rich context, chat sessions, patterns/correlations, hydration/performance factors.  
4. Live Open-Meteo verified after egress approval (`mode=live`).  
5. Frontend: Google Health / Takeout as primary Settings path; Fitbit labeled legacy fixture; FITINDEX CSV + OCR (no scale OAuth).

---

## 4. Intentionally deferred / cancelled

| Feature | Disposition |
|---|---|
| Live Fitbit data pull as primary sync | **Cancelled as primary** — keep fixture scaffold only (`docs/CONNECTORS.md`) |
| FITINDEX / body-scale vendor OAuth | **Never used — do not implement** |
| Live Google Calendar OAuth | Deferred until Google client secrets; fixture events work |
| Live Google Health API (beyond Takeout) | Deferred until Google credentials; Takeout ZIP is primary import today |
| Full Recharts Vite SPA | Conflicts with single-process static serve |
| ChromaDB | Product chose SQLite memory |
| Multi-user isolation | Local single-user MVP |
| APScheduler background jobs | Superseded: lightweight daemon `BackgroundSyncLoop` (S1) |
| Claude-required extraction | Keep Ollama optional + heuristic |

---

## 5. Credentials still optional

- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` — Calendar live (+ future Health)
- `AEGIS_TOKEN_KEY` — local token encryption for Google tokens
- `FITBIT_CLIENT_*` — **not required for product path**; legacy scaffold only
- Open-Meteo: no key; egress allowed → live mode works

---

## 6. Evidence

| Check | Result |
|---|---|
| `make os-test` | Green on PR #31 tip (see CI) |
| Open-Meteo live smoke | `mode=live` |
| Connector policy | `docs/CONNECTORS.md` |
| PR | https://github.com/StanchPillow55/aegis/pull/31 |
| Remote `legacy-aegis` | **not modified** |
