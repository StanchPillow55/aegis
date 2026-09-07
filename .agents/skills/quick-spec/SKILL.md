---
name: quick-spec
description: Lightweight flow for well-understood work. Use this when the user runs `/quick-spec <feature>`.
---
# Quick Spec Phase

Your goal is to perform a fast-path initialization for well-understood work.
Please read the `kiro-core` skill at `.agents/skills/kiro-core/SKILL.md` for context.

**Steps**:
1. Inspect the repository.
2. Generate `requirements.md` -> `design.md` -> `tasks.md` -> `validation.md` in ONE pass without intermediate approval.
3. Maintain the same quality bar and Definition of Done as the full spec process. This command simply removes planning gates, not validation.
4. Report that the spec is ready, or proceed to implementation if the user requested it.
