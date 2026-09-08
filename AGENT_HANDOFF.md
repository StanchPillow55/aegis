# AGENT_HANDOFF — aegis

**Read first:** `docs/PRODUCT_SPEC.md` · `docs/FEATURE_MERGE_MATRIX.md` · `success_criteria.yaml` · `CLAUDE.md`

## Current state

Feature aggregation on `cursor/feature-merge-aggregate-766c` / [PR #29](https://github.com/StanchPillow55/aegis/pull/29).

Older prototype is available as a **read-only** tree:

- Remote: `origin/legacy-aegis` (`9a4e50e…`)
- Local: `/workspace/legacy-aegis` (via `git archive`; gitignored; do not modify remote)

| Slice | Status |
|---|---|
| 0–6 prior slices | Done |
| Feature merge (PRODUCT_SPEC gaps) | Done + CI green |
| Legacy re-audit + residual ports | Done locally (this pass) |

Local validation: `make os-test` — **103** pytest passed. Live Open-Meteo: **`mode=live`**.

## Ported from legacy this pass

- Safety language guardrails (chat)
- Fitbit OAuth scaffold (`/api/fitbit/status|auth|callback`) — honest `needs_credentials`
- FITINDEX OCR (`/api/fitindex/ocr`) + NL text draft
- Takeout JSON Data Points parser
- Calendar lifestyle signals
- Rich `/api/context/screen` + chat sessions
- Patterns: trend / weekly / correlate / predictors
- Hydration + performance as score **factors** (not top-level contract)

## Known limitations

- Live Fitbit/Calendar **data pull** still needs real OAuth secrets + browser callback
- Vision OCR needs local Ollama `llava`
- Full Grafana/Vite SPA not ported (static overview kept)
- Chroma / multi-user skipped by design
- Cloud Agent `127.0.0.1` ≠ laptop browser — see `docs/bugs/BUG-LOCALHOST-01.md`

## How to open the UI

```bash
make os-dev   # or: make dev
# http://127.0.0.1:8000/ on the same machine
make os-health
```

## Refresh legacy mirror (read-only)

```bash
git fetch origin legacy-aegis
rm -rf /workspace/legacy-aegis && mkdir -p /workspace/legacy-aegis
git archive origin/legacy-aegis | tar -x -C /workspace/legacy-aegis
```

## Rules

Pass criteria only with verify + artifact. Never fake OAuth or live weather success. Do not push to `legacy-aegis`.
