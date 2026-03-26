# Feature Specification: Phase 6 Deployment and End-to-End Validation

**Feature Branch**: `003-deployment-e2e-validation`  
**Created**: 2026-03-26  
**Status**: Draft  
**Input**: User description: "I want deployment tests for phase 6: validation of UI and API deploy/build behavior, an end-to-end local+cloud flow validation, SQL registry validation, and explicit verification that embeddings and BERTopic behavior is correct."

## Clarifications

### Session 2026-03-26

- Q: How should the validation suite handle E2E checks if incremental mode finds zero new posts? -> A: Automatically switch to full-rescrape validation mode and require at least one processed post.
- Q: What should count as a passing embedding reliability outcome when online artifact download is blocked? -> A: Pass if either trusted online download works or configured local fallback works; fail only if both are unavailable.
- Q: For pass/fail, how strict should SQL verification be across required registry tables? -> A: All required tables must meet expected minimum updates in the same run; otherwise fail.
- Q: What readiness timing policy should be used for deployment validation? -> A: Retry for up to 5 minutes, then fail if still not ready.
- Q: Which table set should be mandatory for SQL pass/fail verification? -> A: posts, post_topics, and topic_runs are mandatory; topic_candidates is optional unless discovery emits candidates.
- Q: What artifact must be produced after validation for clone-to-deploy automation? -> A: Cross-platform deployment scripts (`.sh` and `.ps1`) plus a deployment runbook (`DEPLOYMENT.md`).

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Validate Deployment Path (Priority: P1)

As the single operator, I want a repeatable deployment validation run so I can trust that the hosted services start correctly and remain reachable after each release.

**Why this priority**: If deployment is unreliable, no ingestion, review, or browsing workflow can be used.

**Independent Test**: Can be fully tested by executing the standard deployment workflow and checking service readiness outcomes.

**Acceptance Scenarios**:

1. **Given** valid deployment configuration, **When** the deployment validation run starts, **Then** service images are built and services start without fatal errors.
2. **Given** services are started, **When** readiness checks run, **Then** API and UI endpoints are reported as reachable and healthy.
3. **Given** deployment validation is complete, **When** the operator prepares repository onboarding, **Then** cross-platform deployment scripts and guide steps are available for clone-to-deploy execution.

---

### User Story 2 - Validate End-to-End Data Flow (Priority: P2)

As the single user, I want an end-to-end validation that processes a small set of saved posts so I know ingestion, topic assignment, and persistence still work across local and cloud boundaries.

**Why this priority**: Deployment is only meaningful if real content can flow from local sync into canonical persistence.

**Independent Test**: Can be fully tested by running one short sync cycle and confirming persisted records for posts and topic artifacts.

**Acceptance Scenarios**:

1. **Given** at least one eligible saved post and valid credentials, **When** an end-to-end validation sync runs, **Then** content is processed and push results indicate successful ingest.
2. **Given** a successful ingest result, **When** persistence checks run, **Then** canonical data records show the new run artifacts in expected tables.
3. **Given** incremental mode returns zero new posts, **When** end-to-end validation continues, **Then** it switches to full-rescrape validation mode and requires at least one processed post.

---

### User Story 3 - Validate Embedding and Topic Discovery Reliability (Priority: P3)

As the single operator, I want explicit validation of embedding and discovery behavior so I can detect configuration or dependency issues before routine runs fail.

**Why this priority**: Embedding and discovery faults can silently degrade classification quality and reduce trust in the library.

**Independent Test**: Can be fully tested by running discovery reliability checks for normal execution and fallback/error paths.

**Acceptance Scenarios**:

1. **Given** embedding-dependent processing is invoked, **When** discovery validation executes, **Then** the run reports either successful embedding availability or a clear actionable failure reason.
2. **Given** a configured local fallback path that is invalid, **When** validation runs, **Then** the run fails with an explicit path validation message.
3. **Given** online embedding download is blocked, **When** a valid local fallback is configured, **Then** embedding reliability validation still passes.

---

### Edge Cases

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right edge cases.
-->

- Deployment completes but one service is unreachable despite running process state.
- Services are still initializing near timeout boundaries.
- End-to-end validation starts with zero new posts in incremental mode.
- Ingest response is successful but persistence verification finds missing rows.
- One or more required registry tables do not meet expected minimum updates.
- Discovery emits zero candidates in a valid run.
- Local-cloud network interruptions occur during push and retry handling is triggered.
- Embedding artifacts cannot be resolved because of environment trust/proxy constraints.
- Online embedding artifacts are unavailable, but local fallback is correctly configured.
- Fallback model path exists but is unreadable due permissions.
- Validation logs are incomplete after a partial failure.
- Clone-time deployment scripts exist but required configuration steps are missing from the deployment guide.

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: System MUST provide a repeatable Phase 6 deployment validation workflow that confirms service build/start outcomes.
- **FR-002**: System MUST verify runtime service readiness after deployment and report pass/fail per service.
- **FR-003**: System MUST validate an end-to-end local-to-cloud processing run that includes ingestion and topic assignment behavior for a small sample scope.
- **FR-004**: System MUST verify that canonical persistence contains run evidence for processed posts and topic-related records after a successful end-to-end run.
- **FR-005**: System MUST capture structured validation evidence for each test step, including command/probe, result status, and timestamp.
- **FR-006**: System MUST include explicit reliability checks for embedding-dependent discovery behavior.
- **FR-007**: System MUST emit clear actionable error outcomes when embedding reliability checks fail due environment trust or dependency issues.
- **FR-008**: System MUST validate fallback-path behavior for local embedding availability and report invalid fallback configuration as explicit validation failures.
- **FR-009**: System MUST support automated execution of the deployment validation suite so results can be repeated without manual reinterpretation.
- **FR-010**: System MUST preserve single-user scope and existing local-auth/cloud-ingest boundaries while running validation.
- **FR-011**: If incremental validation finds zero new posts, system MUST automatically execute full-rescrape validation in the same run and require at least one processed post for end-to-end pass eligibility.
- **FR-012**: Embedding reliability validation MUST pass when either trusted online embedding availability succeeds or a configured local fallback is validated as usable.
- **FR-013**: Embedding reliability validation MUST fail when both trusted online embedding availability and local fallback availability are not satisfied.
- **FR-014**: SQL registry verification MUST require all required tables to meet expected minimum update thresholds in the same run; otherwise the validation run fails.
- **FR-015**: Service readiness validation MUST retry within a bounded window of up to 5 minutes and fail if required services remain unready after that window.
- **FR-016**: Required SQL pass/fail tables are posts, post_topics, and topic_runs; topic_candidates is required only when the validated run emits one or more discovery candidates.
- **FR-017**: Validation deliverables MUST include executable cross-platform deployment scripts: one shell script (`.sh`) and one PowerShell script (`.ps1`).
- **FR-018**: System MUST provide a `DEPLOYMENT.md` guide that documents required pre-configuration and exact CLI actions to deploy the full project from a fresh clone.

### Key Entities *(include if feature involves data)*

- **Deployment Validation Run**: A single execution record containing environment context, start/end times, overall status, and summary.
- **Service Readiness Check**: A per-service validation result that records readiness outcome and evidence details.
- **End-to-End Validation Result**: A run summary covering sample processing counts, ingest outcome, and run identifiers.
- **Persistence Verification Record**: A per-check record showing expected vs observed canonical registry evidence after ingest.
- **Embedding Reliability Check**: A result record for embedding and discovery checks, including fallback-path and error-path outcomes.

## Constitution Alignment *(mandatory)*

<!--
  ACTION REQUIRED: Explicitly map this feature to constitution constraints.
  Every item below must be addressed with concrete statements.
-->

- **Single-user impact**: Validation scope remains single-user; no multi-user behavior is introduced.
- **Privacy boundary impact**: LinkedIn authentication remains local-only; validation does not move credentials/session state to cloud.
- **Sync model impact**: Validation exercises existing JSON delta ingest behavior and idempotent cloud persistence expectations.
- **Classification impact**: Validation checks embedding/discovery reliability without changing stable-label-first policy.
- **Cost/ops impact**: Validation reuses existing local/cloud stack and does not require paid external services.
- **Persistence/backup impact**: Validation includes canonical persistence checks and does not introduce DB-file replacement behavior.
- **Observability/reproducibility impact**:
  Validation outputs include structured evidence sufficient to reproduce pass/fail outcomes.

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: 100% of mandatory deployment validation steps produce explicit pass/fail outcomes and evidence records in each run.
- **SC-002**: In a validation run with sample eligible posts, end-to-end processing completes with successful ingest in at least 95% of runs.
- **SC-003**: Canonical persistence verification confirms expected minimum updates for all required registry tables in 100% of successful ingest runs.
- **SC-004**: In runs without emitted discovery candidates, SQL validation still passes when all mandatory tables (posts, post_topics, topic_runs) meet thresholds.
- **SC-005**: Embedding reliability checks provide actionable diagnostics for 100% of detected failures, including fallback-path validation errors.
- **SC-006**: Validation execution and reporting for a standard run completes within 20 minutes in normal operating conditions.
- **SC-007**: Required services reach ready status within 5 minutes in at least 95% of validation runs.
- **SC-008**: In a fresh clone workflow, operators can execute documented pre-configuration and complete deployment using the provided `.sh` or `.ps1` script path with no undocumented steps.

## Assumptions

- Validation targets the existing deployment and runtime workflow rather than introducing a new runtime architecture.
- The operator can provide at least one or two sample saved posts when strict end-to-end ingest evidence is needed.
- Canonical persistence remains queryable for verification during validation windows.
- Embedding failures may occur in some environments and should be treated as diagnosable validation outcomes rather than silent skips.
