# aegis MVP Product Spec

**Status date:** 2026-09-07 (screenshot QA)  
**Runtime posture:** local-only / open-source (no paid cloud APIs)  
**Input posture:** text-primary with optional voice dictation; spoken TTS opt-in  
**Source of truth for done:** `success_criteria.yaml` (MVP-* rows)

---

## 1. Product contract

Aegis emits **one evidence-bound daily training directive** for functional longevity from a daily training / recovery / nutrition update.

A complete local MVP must:

1. Accept today’s update (text; optional local STT).
2. Extract structured intake.
3. Score the athlete on the **contract four-score model**.
4. Retrieve **deduplicated historical evidence**, clearly separated from today’s intake.
5. Negotiate / modify today’s WOD when mobility or readiness requires it.
6. Compose **one** directive with explicit evidence citations + safety disclaimer.
7. Optionally speak the directive (opt-in TTS).
8. Persist logs durably on disk across restarts.

---

## 2. What has been accomplished (Sept 7 screenshot)

Aegis is past a migration scaffold. A **working local vertical slice** exists:

`Text input → structured intake → local scoring → evidence retrieval → daily directive`

### Demonstrably working

| Capability | Evidence |
|---|---|
| Local app at `127.0.0.1:8000` | Screenshot / `make os-dev` |
| Text intake UI | Composer textarea + submit |
| Structured extraction | sleep, soreness, meals, WOD, subjective readiness |
| Daily training directive | e.g. “Green light for a full session… add a clear protein source…” |
| Numeric scores shown | readiness, sleep, soreness, diet |
| Evidence / context panel | Intake + evidence JSON |
| Memory hits + log IDs | Retrieval wired; IDs generated |
| Local-first messaging | Footer: “Local-first · Ollama optional · Text primary” |
| Ollama optional | Heuristic fallback when Ollama absent |
| OS foundation gates | All `OS-*` / `AGENT-*` criteria `pass: true` |

### Honest maturity label

**Working local text-based directive prototype with basic evidence retrieval and scoring.**

Not yet the complete product: voice-capable four-score evidence-bound functional-fitness copilot with WOD negotiation and front-rack analysis.

---

## 3. Drift from original product contract

| Original contract | Current implementation | Gap |
|---|---|---|
| Scores: **Front-rack, Sleep, Diet, Workout preparation** | Scores: **Readiness, Sleep, Soreness, Diet** | Front-rack + workout-prep missing; soreness/readiness are stand-ins |
| Voice-first primary input | Text-primary UI; Dictate button present | Voice not demonstrated as reliable path |
| Spoken directive path | `tts: null` in screenshot | Opt-in TTS not proven |
| Macro Pool / diet ledger | Simplified meal/protein heuristic | No real macro ledger |
| WOD negotiation | Movements parsed into intake only | No modify / substitute / scale logic |
| Evidence-bound with conflict handling | Duplicate identical memory hits; history can contradict today | Dedup + source priority missing |
| Safety disclaimer | Not in UI | Required copy missing |
| Durable local persistence | Log ID exists | Restart-proof durability + UX not proven |

### UX issues observed in screenshot

1. **Duplicate evidence** — two identical “Sleep: poor, 6.0h … Readiness: low” hits.
2. **Today vs history conflict** — input “Slept 8 hours” vs retrieved 6h poor sleep; no priority labeling.
3. **Soreness 100 misread risk** — 100 means “no soreness / recovered,” not “maximally sore.” Needs clearer label (e.g. “Recovery (soreness)” or invert presentation).
4. **Missing safety disclaimer.**

---

## 4. Target score model (restore contract)

Replace the current four UI scores with:

| Score | Meaning (0–100, higher = better for training today) | Primary inputs |
|---|---|---|
| **Front-rack** | Overhead / front-rack mobility readiness | shoulder/wrist/thoracic notes, front-rack discomfort, related soreness |
| **Sleep** | Recovery from last night | hours + quality |
| **Diet** | Fueling adequacy vs Macro Pool targets | meals, protein, cumulative daily macros |
| **Workout preparation** | Readiness to execute *today’s specific WOD* | WOD movements × soreness/mobility × subjective readiness |

**Implementation note:** Keep internal soreness as a *factor* feeding Front-rack and Workout preparation, not as a top-level product score. Retire “Readiness” as a displayed top-level score (or keep it only as a derived summary chip, not one of the four).

---

## 5. Feature backlog (to build)

### P0 — Match the product contract (MVP blockers)

#### F1. Four-score restore
- Add `front_rack` and `workout_preparation` scorers.
- Map/remove UI scores to: Front-rack · Sleep · Diet · Workout prep.
- Relabel any recovery/soreness factor so “100 ≠ severe.”
- Tests: golden intakes covering each score band.

#### F2. Evidence source model + conflict handling
- API/UI must separate:
  - `today` — current intake (authoritative for today’s directive)
  - `history` — retrieved prior logs (supporting context only)
- When history contradicts today (e.g. sleep hours), show conflict note; **today wins** unless user explicitly anchors on history.
- Deduplicate memory hits by content hash / near-duplicate cosine threshold.
- Exclude the just-written log from “historical evidence.”

#### F3. Durable local persistence
- Prove SQLite file survives process restart (`data/aegis_memory.sqlite3`).
- Recent-logs endpoint + UI strip showing prior days.
- Migration-safe schema version field.

#### F4. Safety disclaimer
- Always-visible short disclaimer on result view and API payload:
  - Not medical advice; stop if pain (vs soreness); consult a professional for injury.
- Validation test asserts disclaimer present in `/api/directive` and HTML.

#### F5. WOD input + negotiation
- Explicit WOD field (paste / structured movements), not only free-text parse.
- Negotiation engine outputs one of: `as_prescribed` | `scaled` | `substituted` | `deferred`.
- Rules driven by Front-rack + Workout prep + movement contraindications (e.g. front-rack limited → substitute front squat / push press variations).
- Directive must cite the negotiation decision.

#### F6. Local voice path (functional, still optional)
- Working browser dictation **or** local faster-whisper path with status UX.
- Opt-in TTS that does not return `tts: null` when enabled and backend/browser speech is available.
- Footer/status must reflect actual capability (“Voice ready” vs “Text only”).

### P1 — Depth that makes the directive trustworthy

#### F7. Macro Pool (diet ledger)
- Daily protein / carb / fat targets (user-configurable defaults).
- Running ledger for the day; Diet score uses pool fill %, not only meal-count heuristic.
- UI: compact remaining-macros line (not a dashboard dump in the hero).

#### F8. Front-rack mobility path
- Structured prompts / extraction for wrists, elbows, shoulders, thoracic extension.
- Front-rack score + suggested mobility primer before loading.
- Links into WOD negotiation for cleans / thrusters / wall balls / front squats.

#### F9. Local LLM quality bar
- When Ollama is up: structured JSON extraction must beat heuristic on a fixture suite.
- Health/UI badge: `extractor=ollama|heuristic`.
- No paid API fallback.

#### F10. Directive quality / evidence binding
- Directive must include:
  - action
  - WOD decision
  - cited score values
  - cited history IDs (or “no prior history”)
  - disclaimer
- Eval fixtures: at least 10 transcript → expected band tests (offline).

### P2 — Hardening / future

#### F11. Local WOD importer without Browserbase (file/URL fetch).
#### F12. Chroma or real embeddings behind memory provider.
#### F13. Kubernetes / MoE serving experiments (explicitly out of MVP).
#### F14. Remove or quarantine dead cloud modules so they cannot confuse local boot.

---

## 6. UX contract (text-first)

### Primary flow
1. Athlete enters today’s update (text or Dictate).
2. Optional: paste/confirm today’s WOD.
3. Submit → see **one directive**, four scores, today vs history, disclaimer.
4. Optional: Speak directive.

### Result layout requirements
- Brand remains hero-level on first viewport.
- Scores: exactly the four contract scores with clear names.
- Evidence panel sections: **Today** | **History** | **Conflicts** (if any).
- No duplicate history rows.
- Disclaimer always visible near the directive.

---

## 7. API contract (target)

`POST /api/directive`

Request:
```json
{
  "text": "string",
  "wod": { "movements": ["string"], "raw": "string" },
  "speak": false
}
```

Response (shape):
```json
{
  "intake": {},
  "scores": {
    "front_rack": {"score": 0, "factors": {}, "rationale": ""},
    "sleep": {"score": 0, "factors": {}, "rationale": ""},
    "diet": {"score": 0, "factors": {}, "rationale": ""},
    "workout_preparation": {"score": 0, "factors": {}, "rationale": ""}
  },
  "wod_decision": {
    "status": "as_prescribed|scaled|substituted|deferred",
    "original": {},
    "modified": {},
    "reasons": ["string"]
  },
  "directive": "string",
  "disclaimer": "string",
  "evidence": {
    "today": {},
    "history": [{"log_id": "", "content": "", "score": 0}],
    "conflicts": [{"field": "sleep.hours", "today": 8, "history": 6, "resolution": "today_wins"}]
  },
  "extractor": "ollama|heuristic",
  "log_id": "string",
  "tts": {"ok": true, "detail": "", "audio_path": null}
}
```

---

## 8. Definition of Done (MVP)

MVP is complete only when all `MVP-*` rows in `success_criteria.yaml` are `pass: true` with artifacts.

Minimum demo script for acceptance:

1. Fresh `make os-dev`.
2. Submit update with sleep, front-rack limitation, meals, and a clean-heavy WOD.
3. Screenshot/API shows four contract scores, WOD scaled/substituted, today≠history labeling, no duplicate hits, disclaimer present.
4. Restart server; prior log still retrievable.
5. With Speak enabled, TTS payload is non-null **or** browser speech plays with explicit status.

---

## 9. Non-goals (this MVP)

- Paid cloud providers (Anthropic, Deepgram, Redis Cloud, Sentry, Browserbase, Fetch/Band).
- Full medical diagnosis or injury rehab programming.
- Multi-user accounts / cloud sync.
- Kubernetes MoE deployment.

---

## 10. Suggested build order

1. F2 evidence model + dedup (fixes screenshot trust issues quickly)
2. F4 disclaimer
3. F1 four-score restore + UI relabel
4. F3 persistence proof
5. F5 WOD negotiation
6. F8 front-rack path (feeds F1/F5)
7. F7 Macro Pool
8. F6 voice functional path
9. F9–F10 quality bar + evals
