# Bug Intake (Spec-Driven)

## Bug title:
## Date:
## Reporter:
## Affected user story:
## Severity:
## Environment:
## Expected behavior:
## Actual behavior:
## Reproduction steps:
## Evidence:
## Suspected scope:
## Is this a behavior change? (yes/no):
## Acceptance criteria for fix:

# SpecKit Triage Decision

## If no behavior change:
- Keep spec unchanged.
- Add/adjust regression tests.
- Implement fix.
- Optionally append a traceability task in tasks.md.

## If behavior change:
- Run speckit-clarify.
- Update spec.md:
  - clarify section (if needed)
  - functional requirements
  - edge cases
  - acceptance scenarios
- If data/contracts/architecture changed, run speckit-plan.
- Run speckit-tasks (or manually add tasks).
- Run speckit-implement for scoped tasks.
- Run speckit-analyze to verify artifact consistency.

# Execution Checklist

- Reproduce bug locally and capture failing test.
- Write regression test first (or same commit as fix).
- Implement minimal fix.
- Run targeted tests.
- Run full relevant suite.
- Update docs if operational behavior changed.
- Mark task complete with short evidence note.

# Definition of Done (Bug)

- Repro no longer fails.
- Regression test exists and passes.
- Spec/task artifacts updated if behavior changed.
- No unintended regressions in nearby flows.
- User-facing behavior and constraints remain aligned with V1 scope.

# Commit Message Template

fix(scope): short bug summary
Why: one line root cause
What:
- added regression test
- fixed logic path X
- updated spec/tasks (if applicable)
Validation:
- list commands/tests run
- key pass results
