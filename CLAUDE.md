# CLAUDE.md — aegis build contract (read this first, every session)

## What aegis is
Voice-first AI copilot. User speaks a daily training/recovery/nutrition update;
aegis emits ONE evidence-bound daily training directive for functional longevity.

## The accountability contract (NON-NEGOTIABLE)
1. `success_criteria.yaml` is the single source of truth ("Definition of Done").
2. NEVER mark a module complete until its SC rows are `pass: true` WITH a linked artifact.
3. Use the agentic loop: Planner/Prompter -> Coder -> Tester -> QA/Validation.
   - Planner & QA = llm-council (multi-model deliberation, see /council).
   - Coder & Tester = you (Claude Code), single-model for speed.
   - QA fails closed: no merge without passing evidence.
4. Every external call MUST emit a Sentry span. Every LLM call MUST be Phoenix-traced.

## Mandatory tooling per module (sponsor track requirements)
- Redis: use redis/agent-skills; vector/memory/context retrieval, NOT plain caching.
- Anthropic: Claude does extraction + directive composition.
- Fetch AI: orchestrator must be REGISTERED and discoverable via ASI:One.
- Band: agent-to-agent messages flow over Band bus.
- Deepgram: voice is the only primary input (STT + TTS). Text is fallback only.
- Arize/Phoenix: ship a before/after grounding eval that shows measurable improvement.
- Sentry: traces + error capture on all hops.
- Browserbase/Stagehand: WOD importer + UI e2e tests.
- Simular/Sai: drives the demo loop; remember the mandatory social post.

## Cost discipline ($30 Claude credits + free Gemini)
- Inner-loop coding: Claude (Sonnet tier).
- Council members default to Gemini Flash (free) + Claude Haiku; Chairman = Claude Sonnet.
- Reserve Claude Opus / full council ONLY for major gates (plan approval, final QA).

## Repo map
backend/{intake,memory,scorers,agents,reasoner,obs} importer/ frontend/ evals/ tests/ council/
