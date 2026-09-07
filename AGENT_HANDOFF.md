# Agent Handoff Document

## Current Status

- Local-only OS foundation is the active track (no paid cloud APIs required).
- FastAPI serves health + intake/directive APIs and the text-first frontend.
- Providers: local LLM (Ollama/heuristic), SQLite memory, speech scaffolds, OTel-style tracing.
- Target hardware: Apple Silicon M2 / 16GB; Linux CI for foundation tests.

## Validation

```bash
make os-test
make os-demo
```

## Next waves (optional)

- Richer Ollama prompting / structured JSON grammar
- Chroma or true embedding model behind the memory provider
- Piper CLI TTS path
- Kubernetes + MoE serving experiments (out of foundation scope)

## Rules

- Do not mark success criteria `pass: true` unless the verify command passed and the artifact field is non-null.
- Missing local services should become skip guards and bucket-list entries, not hard failures.
