---
name: spec-status
description: Use this workflow when the user runs `/spec-status <spec-name>` to report current requirement/task/validation status without changing implementation.
---
# Spec Status Phase

Your goal is to report the current status of the spec.

**Steps**:
1. Read `.kiro/specs/<spec-name>/requirements.md` (or list them if not yet created).
2. Read `design.md`.
3. Read `tasks.md` and check completion status (`[ ]` vs `[x]`).
4. Read `validation.md` (if it exists).
5. Provide a summary of:
   - What phase the spec is currently in.
   - Tasks completed vs remaining.
   - Next recommended action (e.g. run `/run-all <spec-name>`, `/design <spec-name>`).
6. Do NOT change implementation or execute tasks during this command.
