# Agent Handoff Document

## Current Status (2026-09-07)

- Local vertical slice is runnable and screenshot-proven:
  text → structured intake → scores → memory hits → daily directive.
- OS foundation success criteria are `pass: true`.
- Product is still an early local alpha vs the original MVP contract.

## Spec

Read **`docs/MVP_SPEC.md`** before implementing features.

Key gaps called out by QA:
- Restore scores to Front-rack / Sleep / Diet / Workout preparation
- Dedup + today-vs-history evidence model
- WOD negotiation
- Macro Pool
- Functional optional voice (TTS not `null` when enabled)
- Safety disclaimer
- Proven durable SQLite persistence

## Validation

```bash
make os-test
make os-demo
# MVP gates (fail until implemented):
python3 scripts/validate_success_criteria.py
```

## Rules

- Do not mark `MVP-*` criteria `pass: true` without a passing verify command and non-null artifact.
- Stay local-only: no paid cloud APIs on the core path.
