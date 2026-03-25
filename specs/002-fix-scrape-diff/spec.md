# Feature Specification: Incremental Scrape Diff Reliability

**Feature Branch**: `002-fix-scrape-diff`  
**Created**: 2026-03-25  
**Status**: Draft  
**Input**: User description: "The scrapping takes too long. I would like to scrape only new saved posts but the diff does not work. Would it be needed to save all the scrapped data in a local file and make a diff of the already-scrapped posts to avoid taking that long? Don't we have a flag to avoid this kind of behaviour?"

## Clarifications

### Session 2026-03-25

- Q: When embedding model download fails due SSL/certificate trust issues, what should V1 behavior be? -> A: Fail the entire sync run immediately with an explicit error.
- Q: How should V1 define remediation for enterprise SSL/proxy environments so embedding downloads can succeed securely? -> A: Require documented installation/configuration of trusted corporate CA/proxy settings; do not support insecure TLS bypass.
- Q: When should V1 enforce the SSL/trust fail-fast check for embedding downloads? -> A: Enforce only when embedding-dependent logic is actually invoked in that run; if not invoked, no failure.
- Q: For embedding availability in restricted-network environments, what should V1 require as the supported fallback? -> A: Support a pre-downloaded local embedding model path as an official fallback when online download is blocked.
- Q: If the local fallback embedding path is configured but the file is missing or unreadable, what should V1 do? -> A: Fail the run with an explicit validation error that names the invalid path and remediation action.

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

### User Story 1 - Fast Incremental Sync (Priority: P1)

As the single user, I want routine sync runs to process only newly saved posts so that sync completes quickly.

**Why this priority**: Sync latency is currently the main blocker to frequent use and timely knowledge capture.

**Independent Test**: Can be fully tested by running two consecutive syncs with no new saves and verifying the second run exits early without reprocessing already known posts.

**Acceptance Scenarios**:

1. **Given** previously synced saved posts and no newly saved posts, **When** a normal sync runs, **Then** it detects already-known content and stops without full backlog scraping.
2. **Given** previously synced saved posts plus newly saved posts at the top of the feed, **When** a normal sync runs, **Then** only the newly saved posts are extracted and prepared for classification and push.

---

### User Story 2 - Reliable Diff Checkpointing (Priority: P2)

As the single user, I want the system to keep a durable local record of already-synced posts so incremental diff behavior is reliable across runs.

**Why this priority**: Incremental mode is only trustworthy if the "already seen" state survives restarts and failures.

**Independent Test**: Can be fully tested by syncing once, restarting the process, and confirming the next run still recognizes previously synced posts.

**Acceptance Scenarios**:

1. **Given** a successful sync run, **When** the next sync starts later, **Then** the previous run's synced identifiers are reused to skip already-known posts.
2. **Given** a failed cloud push, **When** the next sync runs, **Then** unsent posts are retried and not incorrectly treated as permanently synced.

---

### User Story 3 - Explicit Full Rescan Control (Priority: P3)

As the single user, I want an explicit override mode to reprocess the full saved-post backlog when debugging extraction behavior.

**Why this priority**: Full rescans are occasionally needed for troubleshooting, but must be intentional to avoid routine slow runs.

**Independent Test**: Can be fully tested by enabling the override and verifying the run does not stop on first previously synced post.

**Acceptance Scenarios**:

1. **Given** full-rescan mode is enabled, **When** a sync runs, **Then** the run processes backlog items beyond the first previously synced post.
2. **Given** full-rescan mode is disabled, **When** a sync runs, **Then** incremental early-stop behavior is restored automatically.

---

### Edge Cases

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right edge cases.
-->

- LinkedIn feed ordering changes temporarily and an older post appears before newly saved items.
- A previously synced post appears with edited text while retaining the same source identity.
- Local checkpoint file is missing or corrupted before sync start.
- Delta push fails after extraction/classification; unsent posts must remain eligible for retry.
<<<<<<< HEAD
=======
- Embedding model download fails due SSL/certificate trust issues and blocks discovery/classification dependencies.
- Corporate proxy/CA is required for outbound model download access.
- Embedding artifacts are unavailable, but the current run path does not require embedding-dependent logic.
- Online embedding download is blocked and local fallback model path is missing or invalid.
- Local fallback embedding path is configured but the file is unreadable due permission or filesystem access errors.
>>>>>>> 4e6836c (Subject:)
- User enables full-rescan mode but forgets to disable it for subsequent routine runs.
- Duplicate saved cards appear in the same extraction window.

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: System MUST support incremental sync behavior that prioritizes newly saved posts and avoids routine full backlog processing.
- **FR-002**: System MUST maintain a local durable checkpoint of previously synced post identities used for incremental diff decisions.
- **FR-003**: During normal incremental runs, system MUST stop scanning when the first already-synced post is encountered.
- **FR-004**: System MUST provide an explicit user-controlled full-rescan mode that bypasses incremental early-stop behavior.
- **FR-005**: System MUST clearly indicate whether a run executed in incremental mode or full-rescan mode in run diagnostics.
- **FR-006**: System MUST preserve unsent posts as unsynced when a delta push fails so they are eligible for automatic retry in later runs.
- **FR-007**: System MUST prevent duplicate canonical post entries when the same saved post is encountered across runs.
- **FR-008**: System MUST keep existing canonical records unchanged when previously synced posts are temporarily absent from a later scrape.
- **FR-009**: System MUST allow the user to return from full-rescan mode to incremental mode without manual state reconstruction.
- **FR-010**: System MUST continue to satisfy existing single-user, local-auth, and idempotent-delta constraints.

- **FR-011**: If required embedding model artifacts cannot be downloaded due SSL/certificate trust failures,
  system MUST fail the sync run immediately and emit an explicit actionable error.
- **FR-012**: System MUST document and support secure enterprise trust/proxy configuration for model
  downloads and MUST NOT provide insecure TLS verification bypass as a supported behavior.
- **FR-013**: SSL/trust fail-fast enforcement for embedding downloads MUST apply only when
  embedding-dependent logic is actually invoked in the active run path.
- **FR-014**: System MUST support an explicit pre-downloaded local embedding model path as an
  official fallback when online model download is blocked by network trust constraints.
- **FR-015**: If a configured local fallback embedding path is missing or unreadable, system MUST
  fail the run with an explicit validation error that includes the invalid path and remediation guidance.

### Key Entities *(include if feature involves data)*

- **SyncCheckpoint**: Local persisted state containing known synced post identities, last successful run marker, and mode-related diagnostics.
- **ScrapeRunMode**: User-selected run intent with two values: incremental or full rescan.
- **SyncRunResult**: Run-level summary containing counts (scraped, new, retried), mode used, and whether push succeeded.
- **PostIdentityRecord**: Canonical identifier representation used to compare newly observed posts against checkpoint state.

## Constitution Alignment *(mandatory)*

<!--
  ACTION REQUIRED: Explicitly map this feature to constitution constraints.
  Every item below must be addressed with concrete statements.
-->

- **Single-user impact**: No multi-user roles or tenancy are introduced; behavior is scoped to one user's local sync workflow.
- **Privacy boundary impact**: LinkedIn authentication/session usage remains local-only; no cloud scraping or credential transfer is introduced.
- **Sync model impact**: Local sync still pushes idempotent JSON deltas; this feature changes only how local incremental candidates are selected.
- **Classification impact**: Classification/discovery boundaries remain unchanged; this feature affects pre-classification scrape scope and retry eligibility.
- **Cost/ops impact**: Faster incremental runs reduce routine runtime cost while preserving an explicit full-rescan path for diagnostics.
- **Persistence/backup impact**: Local checkpoint durability is required; canonical cloud backup/restore strategy remains unchanged.
- **Observability/reproducibility impact**:
  Run metadata must capture selected mode, early-stop activation, retry eligibility, and push outcome for auditability.

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: In incremental mode with no new saved posts, sync completes without backlog reprocessing in at least 95% of runs.
- **SC-002**: In incremental mode, at least 95% of newly discovered saved posts are ingested and classified in a single run.
- **SC-003**: When full-rescan mode is enabled, 100% of posts reachable in the current saved-post scope are considered for processing in that run.
- **SC-004**: After a push failure, 100% of unsent posts remain eligible for automatic retry in the next run.

## Assumptions

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right assumptions based on reasonable defaults
  chosen when the feature description did not specify certain details.
-->

- User runs local sync repeatedly and expects most runs to handle only recent additions.
- Saved-post identity values remain sufficiently stable across runs for checkpoint-based diffing.
- Full-rescan mode is used intentionally for diagnostics, validation, or controlled backfill, not as routine default behavior.
- Existing cloud ingest idempotency and authentication flows remain available and unchanged.
