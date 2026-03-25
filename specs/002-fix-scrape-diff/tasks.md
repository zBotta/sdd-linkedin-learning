# Tasks: Incremental Scrape Diff Reliability

**Input**: Design documents from `/specs/002-fix-scrape-diff/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: No new test-authoring tasks are included because tests were not explicitly requested in the feature spec. Validation and regression execution tasks are included.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Align feature-scope configuration and documentation entry points

- [X] T001 Add feature configuration section for mode/fallback behavior in specs/002-fix-scrape-diff/quickstart.md
- [X] T002 Add environment variable placeholders and comments for embedding fallback path in .env.example
- [X] T003 [P] Add sync behavior contract references to feature docs in specs/002-fix-scrape-diff/contracts/sync-behavior.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core sync-state and retry infrastructure that all stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Implement safe checkpoint load defaults for missing/corrupt state in local_sync/state_store.py
- [X] T005 Implement in-run push retry policy (max 3, exponential backoff) in local_sync/push_client.py
- [X] T006 [P] Add run diagnostics fields for retry/mode visibility in local_sync/sync_agent.py
- [X] T007 Implement authoritative mode resolution (`incremental` vs `full_rescrape`) in local_sync/sync_agent.py
- [X] T008 [P] Add config parsing for local embedding fallback path in local_sync/config.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Fast Incremental Sync (Priority: P1) 🎯 MVP

**Goal**: Ensure routine runs process only newly saved posts and stop early on known content.

**Independent Test**: Run two consecutive syncs with no new saves and verify second run exits without backlog processing.

### Implementation for User Story 1

- [X] T009 [US1] Enforce stop-on-first-seen behavior using checkpoint identities in local_sync/linkedin_scraper.py
- [X] T010 [US1] Pass seen identities and incremental stop controls from orchestrator to scraper in local_sync/sync_agent.py
- [X] T011 [US1] Ensure run output consistently reports effective mode and counts in local_sync/sync_agent.py
- [X] T012 [US1] Align quickstart incremental validation steps with implemented behavior in specs/002-fix-scrape-diff/quickstart.md

**Checkpoint**: User Story 1 is independently functional and demonstrable

---

## Phase 4: User Story 2 - Reliable Diff Checkpointing (Priority: P2)

**Goal**: Make checkpoint updates retry-safe so failed pushes remain eligible for next-run resend.

**Independent Test**: Simulate push failure then recovery and verify unsent posts retry and checkpoint updates only after success.

### Implementation for User Story 2

- [X] T013 [US2] Update sync flow to mark posts as synced only after successful push in local_sync/sync_agent.py
- [X] T014 [US2] Preserve failed-push posts as unsynced and retryable in local_sync/state_store.py
- [X] T015 [US2] Surface retry attempt outcomes and final push disposition in local_sync/sync_agent.py
- [X] T016 [US2] Update push behavior contract with retry/unsynced semantics in specs/002-fix-scrape-diff/contracts/sync-behavior.md

**Checkpoint**: User Stories 1 and 2 are independently functional

---

## Phase 5: User Story 3 - Explicit Full Rescan Control (Priority: P3)

**Goal**: Preserve explicit full-rescan control while defining secure embedding availability behavior for restricted networks.

**Independent Test**: Enable full-rescan mode and verify no early-stop; validate embedding-dependent runs fail fast on trust/path errors with explicit remediation.

### Implementation for User Story 3

- [X] T017 [US3] Enforce full-rescan override behavior independent of stop-on-seen path in local_sync/sync_agent.py
- [X] T018 [US3] Implement embedding-dependent fail-fast behavior for SSL trust download failures in local_sync/topic_discovery.py
- [X] T019 [US3] Implement local embedding model fallback path loading for restricted networks in local_sync/topic_discovery.py
- [X] T020 [US3] Validate fallback embedding path existence/readability with explicit error message in local_sync/topic_discovery.py
- [X] T021 [US3] Document secure CA/proxy remediation and local fallback usage in specs/002-fix-scrape-diff/quickstart.md

**Checkpoint**: All user stories are independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final consistency, regression execution, and documentation alignment

- [X] T022 [P] Update user-facing operational guidance for new sync/error behavior in README.md
- [X] T023 Reconcile feature artifacts with implemented clarifications in specs/002-fix-scrape-diff/plan.md
- [X] T024 Execute feature quickstart validation steps and record outcomes in specs/002-fix-scrape-diff/quickstart.md
- [X] T025 [P] Run targeted regression suite and capture command/results notes in specs/002-fix-scrape-diff/research.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: Depend on Foundational phase completion
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2)
- **User Story 2 (P2)**: Can start after Foundational (Phase 2); relies on US1 orchestration outputs for retry-safe mutation checks
- **User Story 3 (P3)**: Can start after Foundational (Phase 2); integrates with mode handling from US1 and reliability semantics from US2

### Within Each User Story

- Mode/state preconditions before scraper/discovery behavior changes
- Core flow changes before docs/contract alignment
- Story checkpoint must be verified before moving to next priority

### Parallel Opportunities

- T003 can run in parallel with T001-T002
- T006 and T008 can run in parallel with T004-T005
- Within US3, T021 can run in parallel after T018-T020 design decisions are stable
- In polish, T022 and T025 can run in parallel

---

## Parallel Example: User Story 3

```bash
# After foundational phase and US3 core design decisions:
Task: "Implement embedding-dependent fail-fast behavior in local_sync/topic_discovery.py"
Task: "Implement local embedding fallback path loading in local_sync/topic_discovery.py"

# Documentation can proceed in parallel once behavior is stable:
Task: "Document secure CA/proxy remediation and fallback usage in specs/002-fix-scrape-diff/quickstart.md"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Validate independent incremental behavior via quickstart scenario

### Incremental Delivery

1. Deliver US1 for immediate runtime reduction
2. Add US2 for retry-safe checkpoint correctness
3. Add US3 for full-rescan control and secure embedding fallback behavior
4. Run polish phase for docs/regression alignment

### Parallel Team Strategy

1. One contributor handles checkpoint/orchestration tasks (T004-T007, T013-T015)
2. One contributor handles embedding/fallback behavior (T018-T020)
3. One contributor handles contracts/docs/validation tasks (T001-T003, T021-T025)

---

## Notes

- [P] tasks are selected only when file/dependency separation permits parallelism.
- All user story tasks include [US#] labels for traceability.
- Tasks maintain local-auth boundary, JSON delta model, and idempotent cloud ingest constraints.
- No insecure TLS bypass behavior should be introduced as part of this feature.
