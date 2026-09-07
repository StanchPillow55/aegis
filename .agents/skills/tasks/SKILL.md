---
name: tasks
description: Use this workflow when the user runs `/tasks <spec-name>` to generate or synchronize dependency-aware tasks.
---
# Task Generation Phase

Your goal is to generate `.kiro/specs/<name>/tasks.md`.
Please read the full instructions for the TASK GENERATION PHASE in the `kiro-core` skill located at `.agents/skills/kiro-core/SKILL.md`.

**Steps**:
1. Read BOTH `requirements.md` and `design.md`.
2. Generate discrete, executable, dependency-aware implementation units.
3. Ensure every task specifies a stable ID, requirements satisfied, dependencies, code areas, and task-specific validation. Include the traceability table at the end.
