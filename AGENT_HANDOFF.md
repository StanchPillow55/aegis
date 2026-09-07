# AGENT_HANDOFF — aegis

**Read first:** `docs/PRODUCT_SPEC.md` · `docs/FEATURE_MERGE_MATRIX.md` · `success_criteria.yaml` · `CLAUDE.md`

## Current state

Feature aggregation branch `cursor/feature-merge-aggregate-766c` ports compatible PRODUCT_SPEC gaps into the canonical workspace (older prototype path not mounted on Cloud Agent).

| Slice | Branch / PR | Status |
|---|---|---|
| 0 Schema/evidence | #24 | Done |
| 1 Source registry | #25 | Done |
| 2–5 Ingestion + fixture connectors | #26 | Done |
| 6–11 Alerts/goals/scores/tools/charts/PWA/Tailscale | #27 | Done |
| Localhost bugfix docs | #28 | Done |
| Feature merge aggregate | #29 `cursor/feature-merge-aggregate-766c` | Done locally + CI green |

Local validation: `make os-test` (pytest **94** passed). CI @ `2342e0a`: success.

## What landed in this aggregate pass

- Takeout ZIP production parser + `/api/takeout/zip`
- Macro Pool wired into diet / canonical scores
- Open-Meteo with honest `live|offline|disabled` modes
- Connector honesty fields (`integration_state`, `live_oauth=false`)
- `/api/chat`, screen context, vision status, date parsing
- Frontend: overview dashboard, sync panel, chart SVG, settings/imports, chat dock
- `make dev` → `os-dev` alias

## Known limitations

- Fitbit/Calendar = **fixture mode** until OAuth secrets + adapters (UI shows needs_credentials)
- Live Open-Meteo needs egress; otherwise labeled offline fixture
- Older prototype at `/Users/bradleyharaguchi/Downloads/aegis` **not readable here** — unique older-only features still U in the matrix
- Vision processes metadata only unless local llava is present
- Full Grafana-style multi-page analytics deferred
- Tailscale mesh setup is operator-owned (`docs/TAILSCALE.md`)
- **Cloud Agent UI trap:** agent `127.0.0.1` ≠ laptop browser — see `docs/bugs/BUG-LOCALHOST-01.md`

## How to open the UI

1. Same machine as the browser: `make os-dev` (or `make dev`) → `http://127.0.0.1:8000/`
2. Prove: `make os-health`
3. Cloud Agent shell + laptop Chrome → expected connection refused

## Next

1. When older prototype is uploaded/synced to `/workspace/legacy-aegis`, re-audit matrix older columns and port residuals  
2. Live OAuth adapters when `FITBIT_*` / Calendar secrets exist  
3. FITINDEX OCR / richer llava path  
4. Playwright E2E against live `os-dev`

## Rules

Pass criteria only with verify + artifact. Distinguish UI presence ≠ backend ≠ live integration ≠ E2E. Never fake OAuth or live weather success.
