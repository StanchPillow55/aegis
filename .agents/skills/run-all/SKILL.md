---
name: run-all
description: Use this workflow when the user runs `/run-all <spec-name>` to execute all incomplete required tasks according to their dependencies.
---
# Run All Tasks Phase

Your goal is to execute the implementation tasks.
Please read the full instructions for the RUN ALL TASKS PHASE in the `kiro-core` skill located at `.agents/skills/kiro-core/SKILL.md`.

**Steps**:
1. Read `requirements.md`, `design.md`, `tasks.md`, and `validation.md` (if it exists).
2. Parse incomplete tasks, build dependency graph, determine executable waves.
3. Implement tasks wave by wave. Validate each task immediately.
4. Only mark `[x]` when validation passes. Fix any failures during task execution.
