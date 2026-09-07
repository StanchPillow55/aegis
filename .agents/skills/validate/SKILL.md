---
name: validate
description: Use this workflow when the user runs `/validate <spec-name>` to run the complete repository-aware validation process and acceptance matrix.
---
# Validation Suite Phase

Your goal is to perform a full validation for the given spec.
Please read the full instructions for the VALIDATION SUITE PHASE and the VALIDATION-DRIVEN REPAIR LOOP in the `kiro-core` skill located at `.agents/skills/kiro-core/SKILL.md`.

**Steps**:
1. Discover project tooling (formatter, linter, test runner).
2. Create/Update `.kiro/specs/<name>/validation.md`.
3. Run Layer 1 (Static), Layer 2 (Automated Tests).
4. Run Layer 3 (Acceptance Validation matrix).
5. Run Layer 4 (Integration/Runtime).
6. Run Layer 5 (Regression).
7. If validation fails, initiate the Validation-Driven Repair Loop.
