# AGENT_HANDOFF — aegis

**Read first:** `docs/PRODUCT_SPEC.md` (canonical) · `success_criteria.yaml` (DoD) · `CLAUDE.md` (build contract)

---

## Current state

Aegis is a **daily training-decision copilot for functional longevity**, expanding into a **local-first personal health copilot** (wearables, body composition, calendar, NL + image logging, environment, scoring, goals, alerts, conversational dashboard).

**In this repository today:** a working **local text-based health-log / directive path**:

`Text → structured intake → local scores → memory hits → one daily directive`

plus OS-foundation scaffolding (local providers, optional Ollama, SQLite memory, simple frontend).

**It is not complete** against the expanded personal-health-copilot specification.

### Verified in this tree (2026-09-07)

| Item | State |
|---|---|
| `make os-test` | **14 passed** (not 48/48) |
| `make os-dev` / `os-demo` | Works; Ollama optional |
| Scores shown | **Transitional:** readiness, sleep, soreness, diet |
| Canonical scores | Front-rack / Sleep / Diet / Workout-prep / Overall — **not implemented** |
| Fitbit / Calendar / FITINDEX / chat / llava / charts / alerts / goals / PWA / Tailscale | **Not present in this tree** (planned; see status table in PRODUCT_SPEC) |

> Do not treat “tests passing” as “product complete.” The suite only covers the current foundation slice.

---

## Known limitations

- Temporary score-label mismatch (`readiness`/`soreness` vs canonical model)
- Evidence retrieval can duplicate hits; today vs history / conflicts not modeled
- SQLite durability/provenance not E2E proven across restart
- WOD negotiation missing
- Safety disclaimer missing
- Macro Pool missing
- Voice: UI controls exist; reliable STT/TTS not demonstrated (`tts: null` observed)
- Missing Fitbit metric coverage + OAuth/token security
- Missing FITINDEX CSV / OCR / manual review workflow
- Missing configurable background + on-demand sync registry
- Missing alert management (defaults + custom)
- Missing goal system with confirmation
- Missing chart-aware LLM tool responses
- Missing conversation search / floating chat / `AIContextProvider`
- Missing mobile PWA + Tailscale hardening
- No E2E acceptance suite for the expanded product
- Dead/legacy cloud modules (Redis/Anthropic/Browserbase paths) may still exist but are out of local-first core

---

## Next implementation order

1. Canonical schema, provenance, and SQLite durability  
2. Source registry and sync status  
3. Complete manual/fixture ingestion  
4. Fitbit and Calendar adapters  
5. FITINDEX OCR/manual ingestion  
6. Alerts and staleness  
7. Goals and progress tracking  
8. LLM query tools and inline charts  
9. Restore the canonical four-score / WOD-directive contract  
10. Mobile/PWA and Tailscale hardening  
11. End-to-end acceptance testing  

**Start next (Slice 0):** schema + provenance + SQLite restart durability + today/history evidence separation.  
Docs/planning gate first — **do not claim connector features until adapters land with `PHC-*` verify commands.**

---

## Rules

- Never mark `MVP-*` or `PHC-*` criteria `pass: true` without a green verify command and non-null artifact.
- Stay local-first: no cloud LLM/DB on the core path.
- External connectors must fail gracefully; fixtures/manual entry keep the app usable.
- Distinguish UI presence vs backend vs live integration vs E2E verification in all status reports.
