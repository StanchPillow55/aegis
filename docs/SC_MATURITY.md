# Success criteria maturity map

**Purpose:** `success_criteria.yaml` `pass: true` means the listed `verify` command succeeded in CI/local automation. It does **not** always mean the product requirement is live-complete or E2E-verified.

**Update this file** whenever maturity changes. Prefer raising maturity with evidence over flipping narrative “done.”

## Maturity enums

| Code | Meaning |
|---|---|
| `verified` | Real intended path exercised (live provider or true E2E) |
| `fixture-verified` | Fixtures/tests prove contract + honesty; live provider not claimed |
| `implemented-but-not-E2E-tested` | Code/UI present; missing Playwright/mobile/operator acceptance |
| `blocked-on-secrets` | Implementation present or scaffolded; needs credentials to verify live |
| `planned` | Required by PRODUCT_SPEC / IMPLEMENTATION_PLAN; not shipped |

## Map (2026-09-08 QA revision)

### Foundation / MVP (generally stronger)

| ID | Maturity | Notes |
|---|---|---|
| AGENT-* / OS-* | `verified` | CI + local scripts |
| MVP-SCORE-01 | `verified` | Canonical scores tested |
| MVP-EVIDENCE-01 | `verified` | Today/history/conflicts |
| MVP-PERSIST-01 | `verified` | SQLite restart |
| MVP-DISCLAIMER-01 | `implemented-but-not-E2E-tested` | API+UI; browser E2E thin |
| MVP-WOD-01 | `verified` | Negotiation unit/API |
| MVP-FRONTRACK-01 | `verified` | |
| MVP-MACRO-01 | `verified` | Wired into diet |
| MVP-VOICE-01 | `implemented-but-not-E2E-tested` | Browser STT/TTS optional |
| MVP-EXTRACT-01 | `fixture-verified` | Heuristic always; Ollama optional |
| MVP-DEMO-01 | `verified` | Script demos |

### PHC expansion (many over-claimed as complete)

| ID | Maturity | Notes |
|---|---|---|
| PHC-FITBIT-01 | `fixture-verified` | Fixture covers metric names; **live pull + full field provenance planned** |
| PHC-OAUTH-01 | `fixture-verified` / `blocked-on-secrets` | No fake backdoors tested; **state/refresh/revoke/encrypt checklist incomplete for live** |
| PHC-FITINDEX-01 | `implemented-but-not-E2E-tested` | CSV/manual/OCR draft APIs; confirm UI + llava click-path incomplete |
| PHC-TAKEOUT-01 | `verified` | CSV+JSON parsers + API tests |
| PHC-CALENDAR-01 | `fixture-verified` | Fixture events; **live OAuth planned** |
| PHC-GEO-01 | `fixture-verified` | API default-off; **consent/revoke/home UI planned** |
| PHC-ENV-01 | `verified` | Live Open-Meteo smoke + offline labeling |
| PHC-SYNC-01 | `implemented-but-not-E2E-tested` | On-demand + registry; **required background loop planned (P1)** |
| PHC-STALE-01 | `fixture-verified` | Stale flags exist; UI/chat warnings incomplete |
| PHC-SQLITE-01 | `verified` | |
| PHC-PROVENANCE-01 | `verified` | |
| PHC-TOOLS-01 | `implemented-but-not-E2E-tested` | Tools API; chat UI tool use incomplete |
| PHC-CHARTS-01 | `implemented-but-not-E2E-tested` | Specs + basic SVG; interactive Grafana-style controls planned |
| PHC-ALERTS-01 | `implemented-but-not-E2E-tested` | API; custom UI, proactive chat, critical dedupe depth planned |
| PHC-GOALS-01 | `implemented-but-not-E2E-tested` | API confirm; NL create, paused status, history UI planned |
| PHC-CHAT-01 | `implemented-but-not-E2E-tested` | In-memory sessions; **SQLite persist/search planned** |
| PHC-VISION-01 | `implemented-but-not-E2E-tested` | Status + OCR endpoint; full llava E2E planned |
| PHC-CONTEXT-01 | `implemented-but-not-E2E-tested` | Context API; regression suite planned |
| PHC-PWA-01 | `planned` / thin | Manifest only; SW/icons/iPhone install planned |
| PHC-TAILSCALE-01 | `planned` / docs | Security doc exists; **authenticated remote acceptance planned** |
| PHC-FALLBACK-01 | `fixture-verified` | Fixtures usable when externals down |
| PHC-SAFETY-01 | `implemented-but-not-E2E-tested` | Disclaimer + guardrails; **dual analysis vs planning labels planned** |
| PHC-DOCS-01 | `verified` | Specs/handoff present |

## Rule for next agents

Before calling a PHC feature “done” in handoff prose:

1. Maturity is `verified`, or intentionally `fixture-verified` as the permanent mode.  
2. Evidence path cited (test, artifact, or manual checklist).  
3. `docs/SC_MATURITY.md` updated in the same PR.
