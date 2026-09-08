# AGENT_HANDOFF — aegis

**Read first (in order):**
1. `docs/PRODUCT_SPEC.md` — product + architecture contract  
2. `docs/IMPLEMENTATION_PLAN.md` — **QA-revised** next-agent plan (required)  
3. `docs/SC_MATURITY.md` — what `pass: true` actually means  
4. `docs/FEATURE_MERGE_MATRIX.md` — legacy vs canonical feature status  
5. `success_criteria.yaml` — DoD automation (verify scripts)  
6. `CLAUDE.md` — build contract  
7. `docs/bugs/BUG-LOCALHOST-01.md` — if UI “won’t open” from a Cloud Agent

---

## TL;DR for a new agent

You are on **canonical** Aegis `/workspace`, branch  
`cursor/feature-merge-aggregate-766c` ([PR #29](https://github.com/StanchPillow55/aegis/pull/29), CI green).

**Foundation through #29 is shipped and CI-green**, but QA clarified that the **operational completion layer is still open**: required background sync, full Fitbit/Calendar live+OAuth security, persistent chat, interactive charts, geo UI, remote/PWA acceptance, and honest maturity labeling.

**Do not** treat `43/43 pass: true` as “product complete.” Use `docs/SC_MATURITY.md`.

Do **not** modify remote `legacy-aegis`. Do **not** fake OAuth or live weather.

---

## Progress (stacked PRs — CI green)

| Slice | PR | Result |
|---|---|---|
| OS local foundation + text UI | #22 | CI green |
| MVP / product spec | #23 | CI green |
| 0 Schema / evidence / disclaimer | #24 | CI green |
| 1 Source registry + sync | #25 | CI green |
| 2–5 Metrics ingest + fixture connectors | #26 | CI green |
| 6–11 Scores, WOD, alerts, goals, tools, charts, PWA, Tailscale docs | #27 | CI green |
| Localhost bugfix docs | #28 | CI green |
| Feature aggregate + legacy residual ports | #29 | CI green |

### Verification (foundation only)

| Check | Result |
|---|---|
| Tests | **103** pytest (`make os-test`) |
| SC automation | **43/43** `pass: true` = verify scripts green — see maturity map |
| Open-Meteo | Live `mode=live` when egress allowed |
| Demos | `make mvp-demo` / `make os-demo` |

---

## What works today (vs what is still planned)

**Works (foundation):** directive loop; canonical scores + Macro Pool; evidence today_wins; SQLite; registry + on-demand sync + stale flags; fixture Fitbit/Calendar/Takeout; FITINDEX CSV/manual/OCR drafts; Takeout CSV+JSON; Open-Meteo honesty; Fitbit OAuth **scaffold**; chat dock (in-memory); tools/patterns APIs; light overview SVG; geo API default-off.

**Not complete (QA):** automatic **background sync** (required); full Fitbit metric live map; OAuth security checklist; SQLite chat persist/search; llava E2E; inline chat charts; NL goals + alert proactive/dedupe depth; Grafana-style chart interactions; geo consent UI; authenticated Tailscale remote + PWA install; Playwright E2E.

---

## Safety: two output modes (enforce)

1. **Health analysis** — observational / non-prescriptive; guardrails on.  
2. **Training planning (directive)** — labeled non-medical decision support; WOD negotiation allowed; disclaimer always; confirm when materially changing the plan.

Do not market the system as “observational only” while emitting unmarked training commands.

---

## Localhost / browser

App is fine on the agent (`curl :8000` OK). Laptop `127.0.0.1` ≠ VM; use port **8000** on the same host.  
`docs/bugs/BUG-LOCALHOST-01.md` · `docs/bugs/tasks.md` · postmortem under `docs/postmortems/`.

---

## Legacy prototype

| Item | Detail |
|---|---|
| Remote | `origin/legacy-aegis` @ `9a4e50e…` — **do not push/modify** |
| Local | `/workspace/legacy-aegis` via `git archive` (gitignored) |

```bash
git fetch origin legacy-aegis
rm -rf /workspace/legacy-aegis && mkdir -p /workspace/legacy-aegis
git archive origin/legacy-aegis | tar -x -C /workspace/legacy-aegis
```

---

## Next work (QA priority list)

### P1 (start here if not merging)
- **Required background sync:** interval, per-source toggle, retries, last-success, stale warnings, on-demand via button/chat/voice  
- **Fitbit:** full metric list (RHR, steps, distance, active minutes, calories, weight, body fat, stress, breathing rate, activities, …) + units/timestamps/source/confidence/provenance; OAuth state/callback/refresh/revoke/encrypt/scopes/no-log-secrets/UI states  
- **Chat:** SQLite persist, searchable history, image refs, llava click-path, tools from UI, inline charts, context regression tests  
- **Goals/alerts:** NL goal create; statuses in-progress/completed/abandoned/paused; confirm-before-complete; history; custom alerts; critical dedupe; proactive chat; stale/missing/conflict tests  

### P2
- Google Calendar live OAuth + read-only ingest  
- FITINDEX confirm UI  
- Interactive charts (click, range, tooltips, goal bands, missing-data, source/time) + inline chat charts  
- Geo consent/revoke/delete/home/threshold UI  
- PWA SW/icons + mobile install test  
- Authenticated Tailscale remote (no DB exposure; routing/CORS/CSRF/rate-limit as needed)  

### P3
- Playwright same-host E2E  
- Mocked OAuth integration tests  
- Offline/source-failure tests  
- M2 performance / local-model resource tests  
- SQLite backup/export/restore tests  

### Recommended slice order
Without secrets: **A (merge) → S1 background sync → S2 chat persist → S3 goals/alerts → S4 interactive charts**  
With secrets: add **S5 Fitbit**, **S6 Calendar/geo**  
Then **S7 remote/PWA**, **S8 Playwright**.

Details: `docs/IMPLEMENTATION_PLAN.md` §4–5.

---

## Rules (non-negotiable)

1. Mark SC complete in prose only when `docs/SC_MATURITY.md` says so — not merely `pass: true`.  
2. Preserve canonical architecture and green tests.  
3. Never fake OAuth, fake weather, or “connected” without tokens.  
4. Fixtures OK if labeled.  
5. UI ≠ backend ≠ live ≠ E2E.  
6. Do not modify `legacy-aegis` remote.  

---

## Quickstart

```bash
python3 -m pip install -r requirements.txt
make os-test
make os-dev    # same machine as browser → http://127.0.0.1:8000/
make os-health
```
