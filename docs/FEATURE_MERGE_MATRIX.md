# Aegis Feature Merge Matrix

**Target (canonical):** `/workspace` — Cursor Cloud workspace / `github.com/StanchPillow55/aegis`  
**Older prototype (read-only source):** `/Users/bradleyharaguchi/Downloads/aegis`  
**Matrix date:** 2026-09-07  
**Merge type:** Semantic feature aggregation (not a Git merge)

## Blocker — older prototype unavailable on this agent

| Item | Detail |
|---|---|
| Requested path | `/Users/bradleyharaguchi/Downloads/aegis` |
| Agent host check | **Path does not exist** on the Cloud Agent VM (Mac filesystem is not mounted) |
| GitHub search | No second public Aegis prototype repo found under `StanchPillow55` |
| User action requested | Zip/upload the tree, push to a cloneable repo, or sync to `/workspace/legacy-aegis` |
| Impact | “Older prototype status” columns below cannot be file-verified. They use **U** = Unavailable for inspection. Where prior planning mentioned reported features, marked **R** = Reported historically (not verified in this run). |

Until the older tree is provided, aggregation proceeds by:
1. Preserving all current-workspace functionality.
2. Closing remaining PRODUCT_SPEC gaps that do not require the older tree.
3. Updating this matrix when the prototype becomes readable.

### Status codes

| Code | Meaning |
|---|---|
| **I** | Implemented (real logic + tests or manual validation) |
| **F** | Fixture / offline mode (deterministic; not live OAuth/API success) |
| **P** | Partial (backend or UI only; missing half) |
| **S** | Stub / contract only |
| **M** | Missing |
| **U** | Unavailable to inspect (older tree) |
| **R** | Reported in prior planning / screenshots (unverified here) |
| **D** | Deferred intentionally |

---

## Matrix

| Feature | Source | Target now | Older | Compatible | Action | Dependencies | Evidence | Final |
|---|---|---|---|---|---|---|---|---|
| Canonical health schema | both (spec) | I | U/R | Y | Keep target | — | `backend/health/schema.py`, tests | **Keep** |
| Provenance tracking | target | I | U/R | Y | Keep | schema | `Provenance`, PHC-PROVENANCE | **Keep** |
| Durable SQLite | target | I | U/R | Y | Keep | — | memory + health DBs, persist tests | **Keep** |
| Content-hash dedup | target | I | U/R | Y | Keep | memory | `test_mvp_evidence` | **Keep** |
| Restart durability | target | I | U/R | Y | Keep | SQLite | `test_mvp_persist` | **Keep** |
| Today/history/conflicts + today_wins | target | I | U/R | Y | Keep | evidence | `test_mvp_evidence` | **Keep** |
| Safety disclaimer | target | I | U/R | Y | Keep | — | API+UI, PHC-SAFETY | **Keep** |
| Source registry + sync status | target | I | U/R | Y | Keep | SQLite sync DB | PHC-SYNC | **Keep** |
| 24h staleness | target | I | U/R | Y | Keep | registry | PHC-STALE | **Keep** |
| Manual NL intake → directive | target | I | U/R | Y | Keep | LLM/heuristic | `/api/directive` | **Keep** |
| Fitbit **fixture** metric coverage | target | F | U/R | Y | Keep fixture; add real OAuth when creds | registry | PHC-FITBIT (fixture) | **Keep F** |
| Fitbit **live OAuth + API** | older R / spec | M | U/R | Y | Scaffold disabled/config state; no fake auth | secrets | blocked without `FITBIT_*` secrets | **Deferred (creds)** |
| FITINDEX CSV + manual review | target | I | U/R | Y | Keep | metrics store | PHC-FITINDEX | **Keep** |
| FITINDEX screenshot/OCR | spec | M | U/R | Y | Add optional local OCR path later | vision/llava | — | **Port next / D** |
| Google Takeout ZIP (real parser) | tests→prod | I | U/R | Y | Production `backend/connectors/takeout.py` + `/api/takeout/zip` | health store | `tests/test_phc_takeout.py` | **Done** |
| Takeout fixture sync | target | F | U/R | Y | Keep for offline demos; label clearly | connectors | sync_takeout_fixture | **Keep F** |
| Calendar read-only **fixture** | target | F | U/R | Y | Keep | connectors | PHC-CALENDAR | **Keep F** |
| Calendar **live Google OAuth** | older R / spec | M | U/R | Y | Disabled/config state until secrets | secrets | — | **Deferred (creds)** |
| Calendar travel detection | older R / spec | M | U/R | Y | Needs calendar + geo | calendar, geo | — | **Deferred** |
| Geolocation privacy contract | target | S/I | U/R | Y | Keep default-off API; never cloud LLM | — | `/api/geo/status` | **Keep** |
| Live Open-Meteo weather/AQI | spec | I/F | U/R | Y | Live client + `mode=live\|offline\|disabled` | network | `/api/environment`, open_meteo | **Done** |
| Front-rack / Sleep / Diet / Workout-prep / Overall | target | I | U/R | Y | Keep | scorers | MVP-SCORE | **Keep** |
| Soreness (factor / transitional) | target | I | U/R | Y | Keep as factor, not top-level contract | — | transitional block | **Keep** |
| Macro Pool diet ledger | test→prod | I | U/R | Y | Wired into diet + canonical `macro_pool` | intake meals | `test_mvp_macro.py` | **Done** |
| WOD negotiation | target | I | U/R | Y | Keep | scores | MVP-WOD | **Keep** |
| Goals + confirm-before-complete | target | I API / P UI | U/R | Y | Keep API; overview shows goals | goals store | PHC-GOALS | **Partial UI** |
| Alerts defaults/custom/history | target | I API / P UI | U/R | Y | Keep API; overview shows alerts | alerts | PHC-ALERTS | **Partial UI** |
| LLM metric-query tools | target | I | U/R | Y | Keep + parse_date tool | metrics | PHC-TOOLS | **Keep** |
| Inline chart **specs** | target | I | U/R | Y | Keep | charts | PHC-CHARTS | **Keep** |
| Inline chart **frontend render** | older R / spec | I | U/R | Y | SVG renderer from `/api/charts/{metric}` | charts API | frontend chart | **Done** |
| Text chat UI + history | older R / spec | I | U/R | Y | `/api/chat` + floating chat dock | tools, memory | `test_phc_chat.py` | **Done** |
| Voice-first (Deepgram) | older hackathon | M (by design) | U/R | N* | Keep optional browser STT/TTS; no Deepgram | local-first | speech provider | **D (local-first)** |
| Image attach / preview / thumbnails | older R / spec | P | U/R | Y | Chat attach + preview + thumb; vision opt-in | chat, files | frontend chat | **Partial** |
| Vision / Ollama llava | older R / spec | I status | U/R | Y | Honest `/api/vision/status` | Ollama | vision_status | **Done (status)** |
| Semantic screen / AIContext | older R / spec | I light | U/R | Y | `/api/context/screen` into chat | chat | PHC-CONTEXT | **Done light** |
| NL date parsing (`dateparser`) | older R / spec | I | U/R | Y | `dateparser` optional + heuristics | pip dep | `tools/dates.py` | **Done** |
| Answers grounded in provenance | target | I | U/R | Y | Chat cites tool sources | tools, chat | chat citations | **Done** |
| Sync status indicator (UI) | older R / spec | I | U/R | Y | Sources/sync panel | `/api/sources` | `#sync-panel` | **Done** |
| Overview dashboard | older R / spec | I light | U/R | Y | Overview: sync, env, alerts, chart | APIs | `#dashboard` | **Done light** |
| Analytics / History pages | older R / spec | P | U/R | Y | History via logs/metrics; analytics = charts | charts UI | — | **Partial** |
| Settings / Fitbit connect controls | older R / spec | I | U/R | Y | Settings + honest Fitbit state + imports | connectors | `#settings` | **Done** |
| PWA installability | target | P | U/R | Y | Manifest present; add icons/SW later | frontend | PHC-PWA thin | **Keep / enhance later** |
| Tailscale security docs | target | I docs | U/R | Y | Keep | — | `docs/TAILSCALE.md` | **Keep** |
| Grafana-style full dashboard | older R / spec | M | U/R | Y | Large UI; defer full Grafana clone | dashboard | — | **D** |
| Fake OAuth / mock auth backdoors | older? / forbidden | Absent (good) | U | N | **Never restore** | — | oauth security test | **Forbid** |
| Hardcoded “live” weather pretending success | target risk | Fixed | U | N | Modes labeled; offline ≠ live | env | open_meteo | **Fixed** |
| Redis / Anthropic / Deepgram / Sentry required path | legacy | Out of core | U/R | N | Keep local-first; quarantine legacy | — | CLAUDE.md | **D / quarantine** |
| Browserbase WOD importer | legacy | Cloud-gated | U | Cond | Optional only with keys; else disabled state | secrets | `importer/` | **Disabled-clear** |
| Connector honesty API | target | I | U/R | Y | `integration_state` + `live_oauth=false` | status.py | interface tests | **Done** |

\*Incompatible with local-first product decision unless reintroduced as optional connector.

---

## Summary counts (target tree, verified)

| Bucket | Approx. count |
|---|---|
| Keep as-is (I) | ~25 |
| Keep fixture-labeled (F) | ~5 |
| Implement / enhance now (no older tree required) | ~12 |
| Deferred (creds / large UI / policy) | ~8 |
| Older-tree inspection | **Blocked** |

## Next implementation slices (this run)

1. ~~Promote Takeout ZIP parser to production + API~~ **Done**  
2. ~~Wire Macro Pool into diet/canonical scores~~ **Done**  
3. ~~Open-Meteo live fetch with explicit `mode=live|offline|disabled`~~ **Done**  
4. ~~Connector status API: configured|needs_credentials|fixture|disabled~~ **Done**  
5. ~~Frontend: sync panel, light dashboard, chart render, settings~~ **Done**  
6. ~~Chat API + floating chat grounded in tools + provenance~~ **Done**  
7. ~~Optional `dateparser` for tool date ranges~~ **Done**  
8. Refresh PRODUCT_SPEC status table + this matrix finals — **in progress**  

When `/Users/bradleyharaguchi/Downloads/aegis` (or a zip/repo) becomes available, re-audit older columns and port any remaining unique features.
