---
name: kiro-core
description: Core runbook for Kiro-style spec-driven development. Defines the phases, rules, and Definition of Done. Read this when orchestrating or executing a spec.
---

# Kiro Spec-Driven Development Core

This skill contains the canonical instructions for executing the Kiro spec-driven development workflow.

## 1. SPEC STORAGE
Use the following persistent structure: `.kiro/specs/<spec-name>/`
Each specification should contain:
- `requirements.md`
- `design.md`
- `tasks.md`
- `validation.md`
Optionally create `execution-log.md` when execution history would materially help debugging or auditing. Use kebab-case for `<spec-name>`. These files are source-controlled project artifacts. Never store important planning exclusively in conversation history.

## 2. REQUIREMENTS PHASE
Before writing requirements:
1. Inspect the repository. Read relevant source files, docs, config, schemas, APIs, tests, conventions.
2. Determine how the requested behavior fits the existing system. Prefer existing patterns.

`requirements.md` must contain:
- **Overview**: Short description.
- **Goals**: What must be accomplished.
- **Non-Goals**: What is explicitly outside scope.
- **User Stories / Use Cases**: Where applicable.
- **Functional Requirements**: Assign stable IDs (REQ-001, REQ-002, etc.). Testable rather than vague. Use EARS-like wording (WHEN <condition> THE SYSTEM SHALL <behavior>).
- **Acceptance Criteria**: Every major requirement must have observable criteria.
- **Edge Cases**: Include failure conditions, partial state, concurrency, permissions, retries, etc.
- **Constraints**: Compatibility, security, performance, dependencies.
- **Open Questions**: Only genuinely unresolved questions. Do not invent product requirements. Infer where reasonable. Ask the user only when it materially affects product behavior.

## 3. TECHNICAL DESIGN PHASE
Must read `requirements.md`, relevant code, architecture, and tests to produce `design.md`. The design must explain HOW every requirement will be implemented.
Include as applicable:
- Existing System Context
- Proposed Architecture
- Files / Modules Affected
- Component Design
- Data Model
- API / Interface Contracts
- Control / Data Flow (use Mermaid diagrams if helpful)
- Error Handling
- Security / Privacy
- Performance / Scalability
- Compatibility / Migration
- Testing Strategy
- Requirement Traceability (Map design back to REQ IDs)
- Alternatives Considered (Only meaningful ones, explain why the chosen one is better)
Do not over-engineer. Prefer the simplest design that completely satisfies requirements and fits conventions.

## 4. TASK GENERATION PHASE
Must read `requirements.md` and `design.md` to generate `tasks.md`. Tasks must be discrete, executable, dependency-aware implementation units.
Structure:
# Implementation Tasks
* [ ] **T001 — <task name>**
  * Requirements: REQ-001, REQ-003
  * Depends on: none
  * Files/areas: ...
  * Objective: ...
  * Implementation notes: ...
  * Validation: ...
Every task MUST specify: unique ID, requirements satisfied, dependencies, implementation objective, code areas, task-specific validation.
Include explicit testing tasks and integration work. Include a traceability table at the end: Requirement -> Design -> Task(s) -> Validation.

## 5. RUN ALL TASKS PHASE
1. Read requirements, design, tasks, and validation.
2. Parse incomplete tasks and build a dependency DAG. Detect circular dependencies. Determine executable waves.
3. For EACH task: mark in progress `[/]`, read context, inspect code, implement, run task-specific validation, inspect diff, confirm it satisfies requirements, and only then mark `[x]`.
Never mark a task complete merely because code was written. A task is complete only after its validation passes.
If a task fails: diagnose, fix, rerun validation, continue until pass or genuine blocker.

## 6. VALIDATION SUITE PHASE
Create/update `validation.md`. Validation must be repository-aware (use actual tools like formatter, linter, tests).
Layers:
1. Static Validation (formatting, lint, type checking, build)
2. Automated Tests (unit, integration, regression, API)
3. Acceptance Validation (Matrix of REQ-ID, Criterion, Method, Result)
4. Integration / Runtime Validation (exercise affected paths, check logs, API responses)
5. Regression Validation (Run largest practical existing regression suite before final completion).

## 7. VALIDATION-DRIVEN REPAIR LOOP
If validation discovers issues (bug, missing behavior, unmet criterion, regression):
1. Determine root cause, map to requirement.
2. Add/reopen task in `tasks.md`.
3. Update `design.md` if architecture changed.
4. Implement repair, validate task, run full validation again.
Repeat until clean. Do not lower/weaken tests to claim success.

## 8. DEFINITION OF DONE
A spec is COMPLETE only when:
1. Every task is `[x]`.
2. Every mapped task passed its validation.
3. Static checks pass.
4. Build/compilation succeeds.
5. Relevant tests pass.
6. Integration checks pass.
7. Every acceptance criterion has explicit validation evidence.
8. No regressions introduced.
9. No unresolved TODOs/FIXMEs.
10. Requirements, design, code are consistent.
11. `validation.md` records final outcome.
Produce a completion report.

## 9. SPEC DRIFT
If existing design is impossible/incorrect: update `design.md`, explain reason, update tasks, ensure requirements satisfied, continue. Do not quietly diverge. Product changes require user input.

## 10. EXISTING CODEBASE DISCIPLINE
Reuse abstractions, follow naming conventions, follow existing dependency choices, respect module boundaries, keep diffs focused.

## 11. SAFETY
Never automatically: delete prod data, deploy prod, rotate credentials, modify billing, force-push, destroy databases, expose secrets. Normal local dev is allowed.
