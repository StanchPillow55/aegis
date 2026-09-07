---
name: kiro
description: Convenience orchestrator. Use this when the user runs `/kiro <feature request>`.
---
# Kiro Orchestrator

Your goal is to initialize a spec for a new feature request.
Please read the `kiro-core` skill at `.agents/skills/kiro-core/SKILL.md` for full context on specs.

**Steps**:
1. Create a logical `<spec-name>` (kebab-case) for the requested feature.
2. Inspect the repository.
3. Run the Requirements Phase (create `requirements.md`).
4. Run the Technical Design Phase (create `design.md`).
5. Run the Task Generation Phase (create `tasks.md`).
6. Create the initial `validation.md` plan.
7. Report to the user that the spec is ready for execution.

**Crucial Note**: Do NOT begin implementation during `/kiro` unless the user explicitly asks for autonomous execution. The user should then be able to run `/run-all <spec-name>` or `/goal Run all tasks...`
