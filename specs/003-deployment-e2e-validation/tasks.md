# Tasks: Phase 6 Deployment and End-to-End Validation

**Input**: Design documents from `/specs/003-deployment-e2e-validation/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: This feature explicitly requires deployment and end-to-end validation tests, so test tasks are included.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., [US1], [US2], [US3])
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize deployment-validation entry points and evidence scaffolding

- [X] T001 Create cross-platform deployment script scaffolds in scripts/deploy_phase6.sh and scripts/deploy_phase6.ps1
- [X] T002 Create validation evidence writer in tests/integration/helpers/validation_evidence.py
- [X] T003 [P] Add validation run output path configuration in .env.example

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build mandatory shared checks required by all user stories

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Implement Podman deployment stage helper in tests/integration/helpers/deployment_runner.py
- [X] T005 [P] Implement readiness probe helper with 5-minute bounded retry in tests/integration/helpers/readiness_probe.py
- [X] T006 [P] Implement strict SQL verification helper in tests/integration/helpers/sql_verifier.py
- [X] T007 [P] Implement embedding reliability helper in tests/integration/helpers/embedding_validator.py
- [X] T008 Implement end-to-end stage helper with incremental->full-rescrape fallback in tests/integration/helpers/e2e_runner.py
- [X] T009 Implement mandatory-stage pass/fail aggregator in scripts/validate_phase6.py
- [X] T010 Add deployment-script output metadata to validation summary in scripts/validate_phase6.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Validate Deployment Path (Priority: P1) 🎯 MVP

**Goal**: Ensure deployment build/start and readiness are validated deterministically.

**Independent Test**: Execute deployment validation only and confirm build success plus readiness success/failure within the 5-minute policy.

### Tests for User Story 1

- [X] T011 [P] [US1] Add deployment stage integration test in tests/integration/test_phase6_deployment.py
- [X] T012 [P] [US1] Add readiness timeout policy integration test in tests/integration/test_phase6_readiness.py

### Implementation for User Story 1

- [X] T013 [US1] Implement deployment stage execution in scripts/validate_phase6.py
- [X] T014 [US1] Implement readiness stage orchestration and result mapping in scripts/validate_phase6.py
- [X] T015 [US1] Persist deployment and readiness evidence records in tests/integration/helpers/validation_evidence.py
- [X] T016 [US1] Add integration test for script entrypoint success path in tests/integration/test_phase6_deployment.py

**Checkpoint**: User Story 1 is independently functional and testable

---

## Phase 4: User Story 2 - Validate End-to-End Data Flow (Priority: P2)

**Goal**: Ensure local-to-cloud processing and strict SQL registry verification are enforced.

**Independent Test**: Run validation with sample posts and confirm push success, fallback to full-rescrape on zero new posts, and required-table SQL gates.

### Tests for User Story 2

- [X] T017 [P] [US2] Add incremental zero-new fallback integration test in tests/integration/test_phase6_e2e.py
- [X] T018 [P] [US2] Add strict SQL required-table gating test in tests/integration/test_phase6_sql.py

### Implementation for User Story 2

- [X] T019 [US2] Implement end-to-end stage orchestration with processed-post requirement in scripts/validate_phase6.py
- [X] T020 [US2] Implement automatic full-rescrape rerun when incremental new_count is zero in scripts/validate_phase6.py
- [X] T021 [US2] Implement SQL verification policy for posts/post_topics/topic_runs and conditional topic_candidates in scripts/validate_phase6.py
- [X] T022 [US2] Emit end-to-end and SQL stage evidence summaries in tests/integration/helpers/validation_evidence.py

**Checkpoint**: User Stories 1 and 2 are independently functional

---

## Phase 5: User Story 3 - Validate Embedding and Topic Discovery Reliability (Priority: P3)

**Goal**: Ensure embedding reliability passes/fails according to secure online-or-fallback rules with actionable diagnostics.

**Independent Test**: Execute embedding validation scenarios for online success, fallback success, and dual-path failure with explicit error output.

### Tests for User Story 3

- [X] T023 [P] [US3] Add embedding pass-when-online-or-fallback test in tests/integration/test_phase6_embedding.py
- [X] T024 [P] [US3] Add invalid fallback explicit-error integration test in tests/integration/test_phase6_embedding.py

### Implementation for User Story 3

- [X] T025 [US3] Implement embedding reliability stage in scripts/validate_phase6.py
- [X] T026 [US3] Implement actionable embedding failure diagnostics mapping in scripts/validate_phase6.py
- [X] T027 [US3] Integrate embedding stage results into final pass/fail aggregator in scripts/validate_phase6.py

**Checkpoint**: All user stories are independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final consistency, documentation, and regression execution

- [X] T028 [P] Update operational validation instructions in specs/003-deployment-e2e-validation/quickstart.md
- [X] T029 Reconcile deployment validation contract wording with implemented behavior in specs/003-deployment-e2e-validation/contracts/deployment-validation.md
- [X] T030 [P] Run targeted regression suite and record results in specs/003-deployment-e2e-validation/research.md
- [X] T031 Execute full phase-6 validation runner and record a sample evidence block in specs/003-deployment-e2e-validation/quickstart.md
- [X] T032 [P] Add clone-to-deploy runbook with CLI steps in DEPLOYMENT.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: Depend on Foundational completion
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Starts after Foundational; no dependency on other stories
- **User Story 2 (P2)**: Starts after Foundational; depends on shared deployment/readiness helpers but remains independently testable
- **User Story 3 (P3)**: Starts after Foundational; can proceed in parallel with US2 once shared helpers are complete

### Within Each User Story

- Tests first, then implementation
- Stage orchestration before evidence output finalization
- Story checkpoint validation before moving to next priority

### Parallel Opportunities

- T003 parallel with T001-T002
- T005-T007 parallel after T004 starts
- T011 and T012 parallel
- T017 and T018 parallel
- T023 and T024 parallel
- T028 and T030 parallel

---

## Parallel Example: User Story 2

```bash
# Run in parallel after foundational tasks:
Task: "Add incremental zero-new fallback integration test in tests/integration/test_phase6_e2e.py"
Task: "Add strict SQL required-table gating test in tests/integration/test_phase6_sql.py"

# Then implement orchestration and policy checks:
Task: "Implement end-to-end stage orchestration in scripts/validate_phase6.py"
Task: "Implement SQL verification policy in scripts/validate_phase6.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Validate deployment and readiness behavior independently

### Incremental Delivery

1. Deliver US1 for deployment confidence
2. Add US2 for end-to-end + strict SQL guarantees
3. Add US3 for embedding reliability assurance
4. Complete polish with regression and evidence logging

### Parallel Team Strategy

1. One contributor handles deployment/readiness path (US1)
2. One contributor handles e2e + SQL gating (US2)
3. One contributor handles embedding reliability path (US3)

---

## Notes

- [P] tasks are selected only when file/dependency separation permits parallelism.
- All story tasks include [US#] labels for traceability.
- Tasks explicitly enforce full-rescrape fallback, strict SQL table gates, and secure embedding reliability behavior.
- No insecure TLS bypass behavior should be introduced.
