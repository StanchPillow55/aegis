# AGENT_HANDOFF — aegis

## Current state (autonomous plan execution)

Implemented through the approved plan on stacked branches:

1. Slice 0 — schema/provenance/evidence/disclaimer (PR #24)
2. Slice 1 — source registry + sync (PR #25)
3. Slices 2–5 — metrics ingestion + fixture connectors (PR #26)
4. **This wave** — alerts, goals, canonical scores, WOD negotiation, LLM tools, charts, PWA manifest, Tailscale docs, geo/env privacy stubs

### Verification
- `pytest tests/ -q` — all green
- `make mvp-demo` / `make os-demo`
- Success criteria: see `success_criteria.yaml` (MVP-* / PHC-* closed with artifacts where verified)

### Still limited / honest gaps
- Fitbit/Calendar/Takeout are **fixture-mode** (no live OAuth tokens)
- Chat/vision/AIContext are thin local stubs (search proxy / optional flags)
- Open-Meteo is offline fixture
- Grafana-style full dashboard UI not built (composer + APIs + PWA manifest)
- Live Tailscale mesh is operator-owned (docs + security rules in `docs/TAILSCALE.md`)

### Next optional hardening
- Live OAuth connectors when credentials available
- Richer chat UI + llava wiring
- Dashboard shell
- Browser E2E against `make os-dev`
