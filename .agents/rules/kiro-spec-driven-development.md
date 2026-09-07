---
name: kiro-spec-driven-development
description: Enforces Kiro-style spec-driven development for all non-trivial engineering work.
trigger: always_on
---

# Kiro-Style Spec-Driven Development Workflow

For any non-trivial task involving new features, multi-file implementation, architectural changes, significant refactoring, API changes, database/schema changes, new integrations, security-sensitive behavior, substantial bug fixes, or changes where regressions would matter: **DO NOT immediately begin coding.**

Instead, use the spec-driven workflow. Tiny, isolated edits such as typo fixes, simple renames, one-line configuration changes, or explicitly requested quick fixes may bypass the full spec process. Never create bureaucracy merely for its own sake.

Specs are stored in `.kiro/specs/<spec-name>/` as source-controlled artifacts.

## Available Workflows / Slash Commands

To execute this workflow, you must use the following skills/commands:
- `/kiro <feature request>`: Convenience orchestrator to initialize a spec.
- `/spec <feature>`: Requirements phase.
- `/design <spec-name>`: Technical design phase.
- `/tasks <spec-name>`: Task generation phase.
- `/run-all <spec-name>`: Execution phase.
- `/validate <spec-name>`: Validation suite.
- `/spec-status <spec-name>`: Report current status.
- `/quick-spec <feature>`: Fast path for well-understood work.

When executing tasks or running under `/goal` for a spec, you must follow the strict validation-driven repair loop and Definition of Done.
For full details on each phase, you MUST load and read the `kiro-core` skill (located in `.agents/skills/kiro-core/SKILL.md`).
