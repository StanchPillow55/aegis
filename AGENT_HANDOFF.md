# AGENT_HANDOFF — aegis

**Read first:** `docs/PRODUCT_SPEC.md` · `success_criteria.yaml` · `CLAUDE.md`

## Current state

Autonomous plan execution complete through stacked PRs:

| Slice | Branch / PR | Status |
|---|---|---|
| 0 Schema/evidence | #24 | Done |
| 1 Source registry | #25 | Done (CI green) |
| 2–5 Ingestion + fixture connectors | #26 | Done |
| 6–11 Alerts/goals/scores/tools/charts/PWA/Tailscale | `cursor/slice6-alerts-goals-scores-766c` | Done locally; CI pending |

**43/43** success criteria marked with artifacts after local verification (`pytest` 87 passed, `make mvp-demo`).

## Known limitations

- Fitbit/Calendar/Takeout = **fixture mode** (no live OAuth credentials in this environment)
- Chat / vision / AIContext are thin stubs (memory search proxy; no full floating chat UI)
- Open-Meteo returns offline fixture
- Full Grafana-style dashboard shell not built (composer UI + rich APIs + PWA manifest)
- Tailscale mesh setup is operator-owned; security contract documented in `docs/TAILSCALE.md`
- Browser E2E against a live `os-dev` server not automated in CI

## Next implementation order

1. ~~Canonical schema / provenance / SQLite~~  
2. ~~Source registry + sync~~  
3. ~~Manual/fixture ingestion~~  
4. ~~Fitbit/Calendar adapters (fixture)~~  
5. ~~FITINDEX CSV/manual~~  
6. ~~Alerts + staleness~~  
7. ~~Goals~~  
8. ~~LLM tools + charts~~  
9. ~~Canonical four-score + WOD~~  
10. ~~PWA manifest + Tailscale docs~~  
11. Optional hardening: live OAuth when secrets available, richer chat/llava, dashboard shell, Playwright E2E  

**Slice 0 complete.** Continue optional hardening only when credentials or UI scope expand.

## Rules

Pass criteria only with verify + artifact. Distinguish UI presence ≠ backend ≠ live integration ≠ E2E.
