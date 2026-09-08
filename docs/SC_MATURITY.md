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

## Map (2026-09-08 Goal Graph revision)

### Foundation / MVP (generally stronger)

| ID | Maturity | Notes |
|---|---|---|
| AGENT-* / OS-* | `verified` | CI + local scripts |
| MVP-SCORE-01 | `verified` | Compat scorers still tested; **dashboard contract migrating to dynamic signals (GG)** |
| MVP-EVIDENCE-01 | `verified` | Today/history/conflicts |
| MVP-PERSIST-01 | `verified` | SQLite restart |
| MVP-DISCLAIMER-01 | `implemented-but-not-E2E-tested` | API+UI; browser E2E thin |
| MVP-WOD-01 | `verified` | Negotiation unit/API |
| MVP-FRONTRACK-01 | `verified` | Provider remains |
| MVP-MACRO-01 | `verified` | Wired into diet |
| MVP-VOICE-01 | `implemented-but-not-E2E-tested` | Browser STT/TTS optional |
| MVP-EXTRACT-01 | `fixture-verified` | Heuristic always; Ollama optional |
| MVP-DEMO-01 | `verified` | Script demos |

### PHC expansion

| ID | Maturity | Notes |
|---|---|---|
| PHC-FITBIT-01 | `fixture-verified` | Fixture covers metric names; live pull planned |
| PHC-OAUTH-01 | `fixture-verified` / `blocked-on-secrets` | Live checklist incomplete |
| PHC-FITINDEX-01 | `implemented-but-not-E2E-tested` | Confirm UI + llava click-path incomplete |
| PHC-TAKEOUT-01 | `verified` | CSV+JSON parsers + API tests |
| PHC-CALENDAR-01 | `fixture-verified` | Fixture events; live OAuth planned |
| PHC-GEO-01 | `fixture-verified` | API default-off; consent UI planned |
| PHC-ENV-01 | `verified` | Live Open-Meteo smoke + offline labeling |
| PHC-SYNC-01 | `fixture-verified` | Background loop S1 |
| PHC-STALE-01 | `fixture-verified` | Stale flags + UI/chat hints |
| PHC-SQLITE-01 | `verified` | |
| PHC-PROVENANCE-01 | `verified` | |
| PHC-TOOLS-01 | `implemented-but-not-E2E-tested` | Expand for Goal Graph tools in GL5 |
| PHC-CHARTS-01 | `implemented-but-not-E2E-tested` | Long-term bands → GL4 |
| PHC-ALERTS-01 | `implemented-but-not-E2E-tested` | |
| PHC-GOALS-01 | `implemented-but-not-E2E-tested` | Thin metric goals; **superseded by GG-*** |
| PHC-CHAT-01 | `implemented-but-not-E2E-tested` | Unified composer; SQLite persist planned (S2) |
| PHC-VISION-01 | `implemented-but-not-E2E-tested` | |
| PHC-CONTEXT-01 | `implemented-but-not-E2E-tested` | Pin context + basic screen API; **typed Goal Graph context → GL5** |
| PHC-PWA-01 | `planned` / thin | Manifest only |
| PHC-TAILSCALE-01 | `planned` / docs | Authenticated remote acceptance planned |
| PHC-FALLBACK-01 | `fixture-verified` | |
| PHC-SAFETY-01 | `implemented-but-not-E2E-tested` | Dual analysis vs planning + HITL suggestions |
| PHC-DOCS-01 | `verified` | Specs/handoff/Goal Graph docs |

### Goal Graph (`GG-*`) — all planned until path tested

| ID | Maturity | Notes |
|---|---|---|
| GG-SCHEMA-01 | `fixture-verified` | GL0 SQLite graph store + HITL suggestion apply; UI/E2E still open |
| GG-SIGNAL-01 | `fixture-verified` | GL1 providers + selection; UI uses selected signals when present; overall optional with goals |
| GG-CONTRIB-01 | `fixture-verified` | GL2 journal→goal contributions (beef/rice/run); UI review still open |
| GG-SUGGEST-01 | `fixture-verified` | HITL approve/edit/reject/defer; no silent task creation; UI panel still open |
| GG-UI-01 | `planned` | GL3 tree/inbox/editor/suggestion panel |
| GG-PROGRESS-01 | `planned` | GL4 long-term progress workspace |
| GG-CONTEXT-01 | `planned` | GL5 typed screen context + tools |
| GG-E2E-01 | `planned` | Full journal→approval→dashboard→chat path |

## Rule for next agents

Before calling a PHC/GG feature “done” in handoff prose:

1. Maturity is `verified`, or intentionally `fixture-verified` as the permanent mode.  
2. Evidence path cited (test, artifact, or manual checklist).  
3. `docs/SC_MATURITY.md` updated in the same PR.  
4. Goal Graph additionally requires the human-approval path in `docs/GOAL_GRAPH.md` §12.
