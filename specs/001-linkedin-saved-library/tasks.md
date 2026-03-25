# Tasks: LinkedIn Saved Posts Knowledge Library (V1)

**Input**: Design documents from /specs/001-linkedin-saved-library/
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ingest-api.yaml

## Format: [ID] [P?] [Story] Description

## Phase 1: Local Sync Prototype

**Goal**: Build a demonstrable local-only sync path that extracts saved posts, normalizes content, and prepares authenticated delta pushes.

**Independent Test**: Run one local sync against a valid browser session and verify normalized delta payloads are produced without cloud-side scraping.

- [X] T001 Create module skeleton for local_sync, cloud, shared, scripts, and tests in local_sync/__init__.py
- [X] T002 Initialize Python project dependencies and tool config in pyproject.toml
- [X] T003 [P] Add environment templates for local agent and cloud endpoint settings in .env.example
- [X] T004 [P] Define shared ingest payload schemas and validation models in shared/schemas.py
- [X] T005 [US1] Implement LinkedIn saved-post extraction via local authenticated browser session in local_sync/linkedin_scraper.py
- [X] T006 [US1] Implement normalization and dedup preprocessing (normalized JSON only) in local_sync/preprocessing.py
- [X] T007 [US1] Implement sync checkpoint/state tracking for incremental runs in local_sync/state_store.py
- [X] T008 [US1] Implement local sync orchestration (extract -> preprocess -> package) in local_sync/sync_agent.py (depends on T005, T006, T007)
- [X] T009 [US1] Implement authenticated JSON delta push client with retry-safe request envelopes in local_sync/push_client.py (depends on T004, T008)
- [X] T010 [P] [US1] Add unit tests for normalization, dedup, and source-key handling in tests/unit/local_sync/test_preprocessing.py
- [X] T011 [US1] Add integration test for one-cycle local sync prototype with fixture data in tests/integration/test_local_sync_prototype.py (depends on T008, T009)

---

## Phase 2: Stable Classification

**Goal**: Deliver stable taxonomy assignment with one primary topic, optional secondary topics, and reproducible run metadata.

**Independent Test**: Classify a fixture batch and verify deterministic primary/secondary assignments, confidence values, and run diagnostics.

- [X] T012 [P] [US1] Seed initial stable taxonomy and thresholds configuration in topics.yaml
- [X] T013 [US1] Implement BERTopic taxonomy assignment module with default local embedding model in local_sync/taxonomy_assignment.py
- [X] T014 [P] [US1] Implement taxonomy versioning and stable-label resolution helpers in shared/taxonomy.py
- [ ] T015 [US1] Implement optional non-blocking summary/label refinement wrapper (disabled-safe) in local_sync/topic_label_refinement.py
- [X] T016 [US1] Extend sync pipeline to persist per-post confidence plus primary/secondary topic roles in local_sync/sync_agent.py (depends on T013, T014)
- [X] T017 [US1] Record classification run metadata and diagnostics payloads in shared/models.py
- [X] T018 [P] [US1] Add unit tests for confidence thresholding and primary-topic uniqueness in tests/unit/local_sync/test_taxonomy_assignment.py
- [X] T019 [US1] Add integration test for stable assignment reproducibility across repeated runs in tests/integration/test_stable_classification.py (depends on T016, T017)
- [ ] T020 [US1] Add local classification telemetry (counts, failures, timing) in local_sync/observability.py

---

## Phase 3: Discovery Pipeline

**Goal**: Add daily discovery over unmatched/low-confidence/recent posts and a manual backlog reprocess workflow.

**Independent Test**: Execute discovery on fixture data, produce topic candidates, and verify manual backlog reprocess updates assignments only when explicitly triggered.

- [X] T021 [US2] Implement discovery orchestration for unmatched, low-confidence, and rolling-window scopes in local_sync/topic_discovery.py
- [X] T022 [US2] Implement candidate labeling and keyword extraction for review queue payloads in local_sync/topic_discovery.py
- [X] T023 [US2] Implement manual backlog reprocess command path (no auto-reprocess) in local_sync/sync_agent.py
- [X] T024 [US2] Extend delta payload assembly for topic candidates and discovery-tagged post topics in local_sync/sync_agent.py (depends on T021, T022)
- [X] T025 [P] [US2] Add unit tests for discovery scope inclusion and exclusion logic in tests/unit/local_sync/test_topic_discovery.py
- [X] T026 [US2] Add integration test for discovery candidate generation and manual reprocess behavior in tests/integration/test_discovery_pipeline.py (depends on T023, T024)
- [X] T027 [US2] Add review decision and reprocess operator guide in docs/review-workflow.md
- [X] T028 [US2] Add discovery telemetry for candidate counts, confidence bands, and backlog age in local_sync/observability.py

---

## Phase 4: Cloud Storage + Ingest API

**Goal**: Deliver authenticated ingest endpoints with idempotent upserts into canonical SQLite (WAL + FTS5), plus review decision APIs.

**Independent Test**: Send duplicate ingest batches and verify idempotent results, live reads, and authenticated access to all defined contract endpoints.

- [X] T029 [P] Create SQLite connection manager with WAL, busy timeout, and transaction helpers in shared/db.py
- [X] T030 Create canonical schema and FTS5 initialization script for posts/topics/post_topics/topic_runs/topic_candidates/notes in scripts/init_db.py
- [X] T031 [US1] Implement idempotent upsert service for ingest batch payloads in cloud/api/services/ingest_service.py
- [X] T032 [P] Implement bearer-auth validation middleware for API routes in cloud/api/auth.py
- [X] T033 [P] [US1] Implement health and sync-status routes matching contract in cloud/api/routes/system.py
- [X] T034 [US1] Implement ingest batch route (POST /ingest/batch) with schema validation in cloud/api/routes/ingest.py
- [X] T035 [US2] Implement topic-runs and topic-candidates decision routes in cloud/api/routes/topics.py
- [X] T036 Wire FastAPI app, route registration, and dependency injection in cloud/api/main.py (depends on T031, T032, T033, T034, T035)
- [X] T037 [P] [US1] Add contract tests for /health, /sync-status, and /ingest/batch in tests/contract/test_ingest_api.py
- [X] T038 [P] [US2] Add contract tests for /topic-runs, /topic-candidates, and /topic-candidates/{id}/decision in tests/contract/test_topic_review_api.py
- [X] T039 [US1] Add integration test for ingest retry/idempotency with duplicate batch IDs in tests/integration/test_ingest_idempotency.py
- [X] T040 [US1] Add API observability for request IDs, ingest counts, and idempotency outcomes in cloud/api/services/telemetry.py

---

## Phase 5: Streamlit UI

**Goal**: Ship authenticated remote UI for Home, Inbox, Topics, Search, Review, Settings, and notes while preserving single-user scope.

**Independent Test**: Authenticate from desktop/mobile browser, browse topics, run FTS search with filters, perform review actions, and create/edit notes.

- [X] T041 [US3] Implement Streamlit app shell and page routing entrypoint in cloud/ui/app.py
- [X] T042 [P] [US3] Implement single-user auth/session gate for hosted UI in cloud/ui/components/auth_gate.py
- [X] T043 [US3] Implement Home and Inbox pages with sync metrics and new-post queue in cloud/ui/pages/home.py
- [X] T044 [US3] Implement Topics page with stable taxonomy and candidate summaries in cloud/ui/pages/topics.py
- [X] T045 [US3] Implement Search page using SQLite FTS5 queries and filters (topic/date/status/source/confidence) in cloud/ui/pages/search.py
- [X] T046 [US2] Implement Review page actions (approve/reassign/adjust/promote/merge/reject/manual reprocess) in cloud/ui/pages/review.py
- [X] T047 [US3] Implement Settings page for taxonomy version, thresholds, and diagnostics summary in cloud/ui/pages/settings.py
- [X] T048 [US3] Implement notes editing panel and persistence wiring in cloud/ui/components/notes_panel.py
- [X] T049 [US3] Add integration smoke test for core UI navigation and authenticated access in tests/integration/test_streamlit_ui_smoke.py
- [X] T050 [US3] Add UI observability cards for last sync, backlog size, and candidate count in cloud/ui/components/status_cards.py
- [X] T051 [US3] Add user documentation for browse/search/review/notes workflows in docs/user-guide.md

---

## Phase 6: Deployment Automation

**Goal**: Provide low-maintenance deployment, health monitoring, restart handling, and safe backup/recovery automation for V1.

**Independent Test**: Bootstrap a fresh EC2 host, bring up API/UI with Docker Compose, run health checks, execute backup + restore drill, and verify quickstart flow.

- [X] T052 [P] Build API container image definition in cloud/Dockerfile.api
- [X] T053 [P] Build UI container image definition in cloud/Dockerfile.ui
- [X] T054 Configure Docker Compose with persistent volume mounts, healthchecks, and restart policies in cloud/docker-compose.yml
- [X] T055 Implement EC2 bootstrap automation with Parameter Store config loading in cloud/bootstrap/ec2_user_data.sh
- [X] T056 [P] Implement runtime health check script for API/UI/DB connectivity in scripts/healthcheck.sh
- [X] T057 Implement SQLite-safe backup automation (backup API or VACUUM INTO pattern) in scripts/backup_db.py
- [X] T058 Implement restore drill script and validation checks in scripts/restore_db.sh
- [X] T059 Configure scheduler scripts for daily discovery and periodic backup jobs in scripts/install_cron.sh
- [X] T060 Add deployment runbook and operations checklist in docs/deployment.md
- [X] T061 Add architecture and module-boundary documentation for local_sync/cloud/shared in docs/architecture.md
- [X] T062 Add V1 scope guardrails (single-user, no cloud scraping, no out-of-scope features) in docs/v1-scope.md
- [X] T063 Add end-to-end quickstart validation test for local sync -> ingest -> UI visibility -> review path in tests/integration/test_quickstart_flow.py

---

## Dependencies & Execution Order

### Phase Dependencies

- Phase 1 can start immediately.
- Phase 2 depends on completion of T001-T011.
- Phase 3 depends on completion of T012-T020.
- Phase 4 depends on completion of T004, T016, and T017, plus schema setup tasks T029-T030.
- Phase 5 depends on completion of T036 and core API contract tests T037-T038.
- Phase 6 depends on completion of Phases 4 and 5.

### Critical Task Chains

- T005 -> T008 -> T009 -> T011
- T013 -> T016 -> T019
- T021 -> T024 -> T026
- T029 and T030 -> T031 -> T034 -> T036 -> T039
- T041 and T042 -> T043/T044/T045/T046/T047/T048 -> T049
- T052/T053 -> T054 -> T055 -> T063

### User Story Delivery Order

- US1 (MVP core): T005-T020 and T031-T040
- US2 (review/discovery): T021-T028, T035, T038, T046
- US3 (remote browse/search/notes): T041-T051

## Parallel Opportunities

- Phase 1: T003 and T004 can run in parallel with T005-T007.
- Phase 2: T012, T014, and T018 can run in parallel once T013 starts.
- Phase 4: T032 and T033 can run in parallel with T031; contract tests T037 and T038 can run together.
- Phase 5: T042 can run in parallel with initial UI shell work in T041; T043-T045 can be split across contributors.
- Phase 6: T052 and T053 can run in parallel; T056 can run in parallel with T055.

## Implementation Strategy

### MVP First

1. Complete Phases 1-2.
2. Complete Phase 4 core ingest path (T029-T034, T036, T037, T039, T040).
3. Validate US1 end-to-end with local sync to cloud ingest.

### Incremental Delivery

1. Add Phase 3 for discovery and review quality.
2. Add Phase 5 for hosted library UX.
3. Add Phase 6 for low-maintenance operations and deployment reliability.

### Scope Control (V1)

- Keep single-user architecture only.
- Exclude multi-user roles, team sharing, and paid-API dependencies from implementation.
- Exclude cloud-side LinkedIn login/scraping automation.
- Defer bulk review editing and advanced candidate-diff tooling.
