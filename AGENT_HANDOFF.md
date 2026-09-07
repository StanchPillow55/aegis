# AGENT_HANDOFF — aegis

**Read first:** `docs/PRODUCT_SPEC.md` · `success_criteria.yaml` · `CLAUDE.md`

## Current state
Local-first health copilot foundation advancing through the approved plan.

### Done
- Slice 0: schema/provenance/evidence/disclaimer
- Slice 1: source registry + sync status
- Slice 2–5 (fixture mode): health metrics store, manual/fixture ingest, Fitbit/Calendar/Takeout fixture connectors, FITINDEX CSV/manual review gate
- Tests: see `pytest tests/ -q`

### Next
6. Alerts + staleness UX  
7. Goals + progress  
8. LLM query tools + chart specs  
9. Canonical four-score + WOD negotiation  
10. PWA + Tailscale docs  
11. E2E acceptance  

## Rules
Pass criteria only with verify + artifact. OAuth live tokens still out of scope (fixture connectors only).
