# AGENT_HANDOFF — aegis

**Read first:** `docs/PRODUCT_SPEC.md` · `success_criteria.yaml` · `CLAUDE.md`

---

## Current state

Aegis is a **daily training-decision copilot for functional longevity**, expanding into a **local-first personal health copilot**.

### Working now (this tree)

- Text → structured intake → transitional scores → memory → daily directive
- **Slice 0 landed:** provenance-backed SQLite logs, schema version, restart durability, evidence bundle with **Today / History / Conflicts (today_wins)**, content-hash dedup, safety disclaimer in API + UI
- OS foundation green; **23** automated tests currently
- Closed criteria include: `MVP-EVIDENCE-01`, `MVP-PERSIST-01`, `MVP-DISCLAIMER-01`, `PHC-SQLITE-01`, `PHC-PROVENANCE-01`, `PHC-DOCS-01`

### Still incomplete

- Canonical scores (Front-rack / Sleep / Diet / Workout-prep / Overall) — UI still shows transitional readiness/soreness
- WOD negotiation, Macro Pool, reliable voice
- Fitbit / FITINDEX / Calendar / sync registry / alerts / goals / LLM tools / charts / PWA / Tailscale — **not in this tree**

---

## Known limitations

- Score-label mismatch remains transitional
- Disclaimer present; full `PHC-SAFETY-01` alert/stale-language suite not done
- No connector adapters yet
- No E2E browser acceptance suite
- Voice Speak still depends on browser/`tts` backends

---

## Next implementation order

1. ~~Canonical schema, provenance, SQLite durability~~ **(done — Slice 0)**
2. **Source registry and sync status** ← next
3. Complete manual/fixture ingestion
4. Fitbit and Calendar adapters
5. FITINDEX OCR/manual ingestion
6. Alerts and staleness
7. Goals and progress tracking
8. LLM query tools and inline charts
9. Restore the canonical four-score / WOD-directive contract
10. Mobile/PWA and Tailscale hardening
11. End-to-end acceptance testing

**Next slice:** Source registry + sync status model (per-source enable, last success/attempt, error, coverage, 24h staleness) with fixture/manual sources first — no live OAuth required.

---

## Rules

- Never mark criteria `pass: true` without green verify + artifact.
- Local-first; connectors fail soft.
- Distinguish UI ≠ backend ≠ integration ≠ E2E in status reports.
