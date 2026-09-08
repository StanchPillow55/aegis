# Feature Merge Decisions

**Date:** 2026-09-08  
**Target:** `/workspace` (`cursor/feature-merge-aggregate-766c`)  
**Older prototype:** `origin/legacy-aegis` → `/workspace/legacy-aegis` (read-only archive; remote branch untouched)

---

## 1. Architectural decisions

| Decision | Choice | Rationale |
|---|---|---|
| Canonical architecture | Current FastAPI + SQLite + static frontend | Passing tests; product local-first |
| Older tree role | Read-only feature source at `/workspace/legacy-aegis` | Extracted via `git archive`; never push to `legacy-aegis` |
| Merge style | Semantic port | Layouts differ (`src/backend` vs `backend`) |
| Score contract | Keep Front-rack/Sleep/Diet/WP/Overall | Hydration/performance ported as **factors** only |
| Chroma | Skip | SQLite memory is DoD |
| Vite/Recharts SPA | Skip wholesale rewrite | Enhance static UI; single `make os-dev` |
| Fake weather / fake OAuth | Forbidden | Legacy silent 22.5°C fallback not ported |

---

## 2. Conflicts and resolutions

| Conflict | Resolution |
|---|---|
| Legacy 6-dim scores vs canonical 5-dim | Canonical wins; hydration/performance → `scores.factors` |
| Legacy Open-Meteo hardcoded fallback | Canonical `live\|offline\|disabled` labeling |
| Legacy “Live Sync” UI badge | Not ported; sync panel shows honest states |
| Calendar OAuth token field mismatch in legacy | Do not port buggy Google token store blindly; signals only for now |
| Fitbit Fernet demo seed | Prefer `AEGIS_TOKEN_KEY` / data-dir-derived key; no fake authenticated |
| Dual-process Makefile (backend+frontend) | Keep single `make os-dev` (+ `make dev` alias) |

---

## 3. Migrations performed (legacy re-audit pass)

1. Fetched `origin/legacy-aegis` → `/workspace/legacy-aegis` (gitignored).  
2. Re-audited matrix with verified **V** older columns.  
3. Ported: guardrails, Fitbit OAuth scaffold, FITINDEX OCR/text drafts, Takeout JSON, calendar signals, rich context, chat sessions, patterns/correlations, hydration/performance factors.  
4. Live Open-Meteo verified after egress approval (`mode=live`).  
5. Frontend: Fitbit status check + FITINDEX OCR upload control.

---

## 4. Intentionally deferred

| Feature | Why |
|---|---|
| Live Fitbit data pull after OAuth | Needs user secrets + callback exercise in real browser |
| Live Google Calendar OAuth | Needs Google client secrets; signals work on fixture events |
| Full Recharts Vite SPA | Conflicts with single-process static serve |
| ChromaDB | Product chose SQLite memory |
| Multi-user isolation | Local single-user MVP |
| APScheduler background jobs | Superseded: lightweight daemon `BackgroundSyncLoop` (S1) — no APScheduler dep |
| Claude-required extraction | Keep Ollama optional + heuristic |

---

## 5. Credentials still optional

- `FITBIT_CLIENT_ID`, `FITBIT_CLIENT_SECRET`, `FITBIT_REDIRECT_URI`, `AEGIS_TOKEN_KEY`
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` (calendar live)
- Open-Meteo: no key; egress now allowed → live mode works

---

## 6. Evidence

| Check | Result |
|---|---|
| `make os-test` | 103 pytest passed |
| Open-Meteo live smoke | `mode=live` |
| PR | https://github.com/StanchPillow55/aegis/pull/29 |
| Remote `legacy-aegis` | **not modified** |
