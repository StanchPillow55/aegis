# AGENT_HANDOFF — aegis

**Read first (in order):**
1. `docs/PRODUCT_SPEC.md` — product + architecture contract  
2. `docs/IMPLEMENTATION_PLAN.md` — **next-agent plan** (progress, gaps, slices A–E)  
3. `docs/FEATURE_MERGE_MATRIX.md` — what was kept / ported / deferred from legacy  
4. `success_criteria.yaml` — Definition of Done (43/43 pass)  
5. `CLAUDE.md` — build contract  
6. `docs/bugs/BUG-LOCALHOST-01.md` — if UI “won’t open” from a Cloud Agent

---

## TL;DR for a new agent

You are continuing **canonical** Aegis at `/workspace` on branch  
`cursor/feature-merge-aggregate-766c` ([PR #29](https://github.com/StanchPillow55/aegis/pull/29), CI green @ `f8a3fed`).

**Autonomous stacked execution through #29 is complete.** Core product + legacy-compatible residuals are in. Next work is merge hygiene, live OAuth (secrets), UI depth, or Playwright — see `docs/IMPLEMENTATION_PLAN.md` §4–5.

Do **not** modify remote `legacy-aegis`. Do **not** fake OAuth or live weather.

---

## Progress (stacked PRs — all CI green when last verified)

| Slice | PR | Result |
|---|---|---|
| OS local foundation + text UI | #22 | CI green |
| MVP / product spec | #23 | CI green |
| 0 Schema / evidence / disclaimer | #24 | CI green |
| 1 Source registry + sync | #25 | CI green |
| 2–5 Metrics ingest + fixture connectors | #26 | CI green |
| 6–11 Scores, WOD, alerts, goals, tools, charts, PWA, Tailscale docs | #27 | CI green |
| Localhost bugfix docs + Makefile/`os-health` | #28 | CI green |
| Feature aggregate + legacy residual ports | #29 | CI green |

### Verification

| Check | Result |
|---|---|
| Local tests | **103** pytest (`make os-test`) |
| Success criteria | **43/43** pass with artifacts |
| Demos | `make mvp-demo` / `make os-demo` |
| Open-Meteo | Live `mode=live` after egress approval |

---

## What works (functionality)

**Directive loop:** text (+ optional Dictate/Speak) → intake → evidence (today/history/conflicts, today_wins) → canonical scores (Front-rack / Sleep / Diet / Workout-prep / Overall) + Macro Pool → WOD negotiation → disclaimer.

**Data:** SQLite durability; source registry + 24h staleness; fixture Fitbit/Calendar/Takeout; FITINDEX CSV/manual/OCR drafts; Takeout CSV+JSON; manual metrics; Open-Meteo live/offline/disabled; geo default-off.

**Intelligence:** chat sessions + guardrails; rich screen context; tools (metrics/alerts/goals/correlate/trend/body_comp/calendar); patterns API; calendar signals; chart specs + SVG; hydration/performance as **factors**.

**UI:** composer + overview (sync/env/alerts/chart) + settings/imports + floating chat.  
**Dev:** `make os-dev` (alias `make dev`) · `make os-health` · port **8000** required.

---

## Localhost / browser (resolved as operator misunderstanding)

Diagnosis (PR #28): app is healthy on the agent (`curl :8000` OK). Laptop Chrome `127.0.0.1` is a different machine; bare `http://127.0.0.1/` hits port 80.  
Docs: `docs/bugs/BUG-LOCALHOST-01.md`, `docs/bugs/tasks.md`, `docs/postmortems/2026-09-07-localhost-connection-refused.md`.

---

## Legacy prototype

| Item | Detail |
|---|---|
| Remote | `origin/legacy-aegis` @ `9a4e50e…` — **do not push/modify** |
| Local mirror | `/workspace/legacy-aegis` via `git archive` (gitignored) |
| Role | Read-only feature source; semantic port only |

Refresh mirror:
```bash
git fetch origin legacy-aegis
rm -rf /workspace/legacy-aegis && mkdir -p /workspace/legacy-aegis
git archive origin/legacy-aegis | tar -x -C /workspace/legacy-aegis
```

---

## Honest gaps → next features

| Priority | Work | Needs |
|---|---|---|
| **P0** | Merge/rebase #22–#29 onto preferred base | Human merge decisions |
| **P1** | Live Fitbit pull after OAuth | `FITBIT_CLIENT_ID/SECRET` + browser |
| **P1** | Live Google Calendar read-only | Google OAuth client |
| **P2** | Goals/alerts editors + FITINDEX confirm UI | No secrets |
| **P2** | Chart goal-band SVG + chat SQLite persistence | No secrets |
| **P2** | PWA icons/SW | No secrets |
| **P3** | Playwright same-host smoke | Browser on server host |
| **Skip** | Chroma, multi-user, Vite SPA rewrite, fake OAuth/weather, boot-required Redis/Deepgram |

**Recommended first slice for a new agent:** Implementation Plan **Slice A** (merge hygiene) or **Slice C** (UI depth without secrets).

---

## Rules (non-negotiable)

1. `success_criteria.yaml` is DoD — mark `pass: true` only with verify + artifact.  
2. Preserve canonical architecture and passing tests.  
3. Never restore fake OAuth, fake weather, or hardcoded “connected” success.  
4. Fixtures OK if labeled; live integrations must show `needs_credentials` / offline when not configured.  
5. Distinguish UI presence ≠ backend ≠ live integration ≠ E2E.  
6. Do not modify `legacy-aegis` remote branch.

---

## Quickstart

```bash
python3 -m pip install -r requirements.txt
make os-test
make os-dev    # same machine as browser → http://127.0.0.1:8000/
make os-health
```
