# Feature Specification: LinkedIn Saved Posts Knowledge Library (V1)

**Feature Branch**: `001-linkedin-saved-library`  
**Created**: 2026-03-24  
**Status**: Draft  
**Input**: User description: "Build a single-user personal knowledge library that ingests LinkedIn Saved posts, classifies them into stable and emerging topics, and exposes authenticated remote browsing and review."

## Clarifications

### Session 2026-03-24

- Q: What extraction strategy should V1 assume for LinkedIn Saved posts? -> A: Always open every saved post detail page and extract full content on each sync run.
- Q: Should V1 persist normalized JSON only, or also raw HTML snapshots? -> A: Persist normalized JSON only; do not persist raw HTML snapshots.
- Q: Should V1 allow one primary topic plus secondary topics, or only one stable label? -> A: Allow one primary stable topic plus secondary topics above a stricter secondary threshold.
- Q: What discovery scope and cadence should V1 use? -> A: Run daily discovery on unmatched posts, low-confidence posts, and a rolling recent window.
- Q: After topic promotion, should old unmatched posts be reprocessed automatically, manually, or not at all? -> A: Reprocess manually via explicit user action; do not auto-reprocess in V1.
- Q: What weak-content enrichment policy should V1 use? -> A: No enrichment in V1; classify only extracted post body from saved post detail pages.
- Q: Should taxonomy assignment run per post or in local batches? -> A: Run in small local batches (default 16) while emitting per-post topic/confidence outputs.
- Q: Should summaries be included in V1, and are they required when local LLM is disabled? -> A: Include summaries as optional enrichments; system remains fully functional when local LLM is disabled.
- Q: What default local models should V1 use for embeddings and topic naming/refinement? -> A: Use all-MiniLM-L6-v2 embeddings and Llama-3.2-3B-Instruct-Q4_K_M (GGUF/llama.cpp) for naming/refinement.
- Q: Which review actions are essential in V1 versus deferrable? -> A: Essential actions are approve assignment, reassign primary topic, adjust secondary topics, promote/merge/reject candidates, and manual backlog reprocess; bulk and advanced audit tooling are deferred.

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

### User Story 1 - Sync and Build My Study Library (Priority: P1)

As a single user, I save posts on LinkedIn and run a local sync that imports new saved posts,
classifies them into stable study topics, and makes them available in my hosted library.

**Why this priority**: Without reliable ingestion and stable classification, no downstream review,
search, or learning workflow is possible.

**Independent Test**: Can be fully tested by running one sync cycle from a local authenticated
session and verifying that newly saved posts appear remotely with topic assignments and sync
metadata.

**Acceptance Scenarios**:

1. **Given** the user has a valid local authenticated LinkedIn browser session and unsynced saved posts,
   **When** the local sync agent runs, **Then** new posts are normalized, deduplicated, classified,
   and pushed as JSON deltas to canonical cloud storage.
2. **Given** a synced post that matches a known taxonomy topic with sufficient confidence,
   **When** classification completes, **Then** the post is assigned to a stable topic and appears
   in the library without requiring UI restart.

---

### User Story 2 - Review Uncertain and Emerging Topics (Priority: P2)

As the user, I review low-confidence assignments and discovered topic candidates so I can keep
taxonomy quality high and promote new study topics when needed.

**Why this priority**: Library quality depends on human-guided correction and controlled taxonomy
evolution.

**Independent Test**: Can be fully tested by loading a review queue containing low-confidence posts
and discovered candidates, then approving, merging, rejecting, and promoting decisions.

**Acceptance Scenarios**:

1. **Given** unmatched or low-confidence posts and generated discovery candidates,
   **When** the user performs review actions, **Then** decisions are persisted and future ingestion
   uses updated stable taxonomy assignments.

---

### User Story 3 - Search, Browse, and Annotate Anywhere (Priority: P3)

As the user, I access my hosted library from phone or work browser, browse by topic, run full-text
search, and add notes to support study and recall.

**Why this priority**: Remote search and annotation convert synced content into a practical personal
knowledge system.

**Independent Test**: Can be fully tested by authenticating remotely, browsing topic pages, running
filtered full-text searches, and creating or editing notes on selected posts.

**Acceptance Scenarios**:

1. **Given** authenticated remote access and indexed library content, **When** the user searches by
  text and filters, **Then** matching posts are returned with relevant topic and status context.

---

### Edge Cases

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right edge cases.
-->

- LinkedIn session is expired locally during sync start.
- A post is edited or removed on LinkedIn after a prior sync.
- Duplicate posts are encountered across multiple sync runs.
- A post has missing author/title fields or unsupported language metadata.
- Classification confidence is below threshold for all stable topics.
- Discovery produces semantically overlapping candidate topics.
- Delta push is retried after partial network failure.
- Ingest receives duplicate deltas for the same post update.
- Remote authentication fails for UI or ingest API requests.
- Backup process runs while the canonical database is serving live queries.

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: System MUST support exactly one user in V1 and MUST NOT implement multi-user roles,
  tenancy, or team workspaces.
- **FR-002**: System MUST run a local sync agent that reads saved LinkedIn posts from the user's
  local authenticated browser session.
- **FR-002a**: Sync extraction MUST open each saved post detail page during sync to capture full
  post content and metadata for normalization and classification.
- **FR-003**: System MUST NOT store LinkedIn credentials, cookies, or browser session state in cloud
  infrastructure.
- **FR-004**: System MUST ingest post text and metadata, normalize content, and deduplicate records
  before persistence.
- **FR-004a**: V1 persistence MUST store normalized structured JSON only and MUST NOT persist raw
  HTML snapshots.
- **FR-004b**: V1 classification input MUST use extracted post body and visible post metadata from
  saved post detail pages only; weak-content enrichment from repost commentary, linked snippets,
  or article-title fallback is out of scope for V1.
- **FR-005**: System MUST classify posts into predefined stable topics using BERTopic-based
  taxonomy assignment with configurable confidence thresholds.
- **FR-005a**: Classification MUST record confidence per candidate topic, assign exactly one
  primary stable topic (highest-confidence match), and allow secondary topic assignments only
  when they pass a stricter secondary threshold.
- **FR-005b**: Stable taxonomy assignment MUST execute in small local batches (default batch size:
  16 posts) and MUST still persist per-post classification outputs and confidence values.
- **FR-006**: System MUST preserve stable topic consistency for known topics across sync runs unless
  taxonomy changes are explicitly approved.
- **FR-007**: System MUST run periodic emerging-topic discovery on unmatched or low-confidence posts.
- **FR-007a**: Discovery scope MUST include unmatched posts, low-confidence posts,
  and a rolling recent window, and MUST run once daily in V1.
- **FR-008**: System MUST generate reviewable topic candidates with human-readable labels and
  representative keywords.
- **FR-009**: System MUST provide review actions for low-confidence assignments and topic candidates:
  approve, merge, reject, and promote.
- **FR-010**: System MUST apply promoted topic candidates to the stable taxonomy for future
  classification runs.
- **FR-010a**: Historical reprocessing after topic promotion MUST be manual and user-triggered
  (for example, "Reprocess backlog") and MUST NOT run automatically in V1.
- **FR-011**: System MUST expose a hosted library UI with pages for Home, Inbox, Topics, Search,
  Review, and Settings.
- **FR-012**: Home page MUST display last sync time, total posts, newly ingested posts,
  discovered-topic candidate count, review backlog size, and topic distribution summary.
- **FR-013**: Inbox page MUST display newly ingested posts with assigned stable topics,
  classification confidence, and review actions.
- **FR-014**: Topics page MUST display stable taxonomy topics, discovered candidates,
  topic detail views, and per-topic post lists.
- **FR-015**: Search page MUST support full-text search across title, content, summary,
  labels, and notes, with filters for topic, date, status, source, and confidence.
- **FR-016**: Review page MUST display low-confidence assignments, unmatched posts,
  and topic candidates awaiting decisions.
- **FR-016a**: Review workflow MUST include an explicit manual action to reprocess backlog items
  against the updated stable taxonomy.
- **FR-016b**: V1 review workflow MUST support approve assignment, reassign primary topic,
  adjust secondary topics, promote candidate, merge candidate, reject candidate, and manual
  backlog reprocess; bulk editing, advanced candidate-diff tooling, and expanded audit UX are
  out of scope for V1.
- **FR-017**: Settings page MUST display taxonomy version, thresholds, sync diagnostics,
  and classification settings summary.
- **FR-018**: System MUST support post annotations through user-managed notes.
- **FR-018a**: Post summaries and cluster summaries MAY be generated in V1 as optional enrichments,
  and summary generation MUST NOT block ingestion, classification, review, or search when local LLM
  capabilities are disabled.
- **FR-019**: System MUST expose authenticated remote access for UI and authenticated ingest API
  access for delta ingestion.
- **FR-020**: System MUST maintain a canonical cloud database and ingest JSON deltas using
  idempotent upserts.
- **FR-021**: Sync behavior MUST NOT require database-file replacement or UI restart.
- **FR-022**: Canonical persistence MUST survive host restarts and failures.
- **FR-023**: System MUST provide automated local sync scheduling, deployment/bootstrap automation,
  health monitoring, restart handling, and backups.
- **FR-024**: Backup and recovery behavior MUST use safe live-database methods.
- **FR-025**: System MUST store classification run metadata, topic/taxonomy versioning,
  and diagnostics needed for audit and reproducibility.
- **FR-026**: V1 MUST NOT require paid LLM or paid API usage for core ingestion and classification.
- **FR-026a**: Default local models in V1 MUST be `sentence-transformers/all-MiniLM-L6-v2`
  for embeddings and `Llama-3.2-3B-Instruct-Q4_K_M` (GGUF via llama.cpp) for optional
  topic naming/refinement.

### Key Entities *(include if feature involves data)*

- **Post**: Canonical saved item from LinkedIn with source identifiers, URL, author,
  published and saved timestamps, normalized title/content, content hash, language,
  metadata payload as normalized JSON, summary, importance/novelty scores, status,
  and lifecycle timestamps.
- **Topic**: Stable taxonomy topic with name, description, version membership,
  active state, and lineage metadata for merges/promotions.
- **PostTopic**: Assignment relationship between Post and Topic including assignment type
  (stable/discovery), confidence, assignment source, and review status.
- **TopicRun**: Execution record for a classification/discovery run with model configuration,
  taxonomy version, timing, counts, and diagnostics.
- **TopicCandidate**: Proposed emerging topic with suggested label, representative keywords,
  evidence set, confidence metrics, and decision state.
- **Note**: User-authored annotation attached to a Post with body text and edit timestamps.

## Constitution Alignment *(mandatory)*

<!--
  ACTION REQUIRED: Explicitly map this feature to constitution constraints.
  Every item below must be addressed with concrete statements.
-->

- **Single-user impact**: Feature is explicitly constrained to one user and excludes all multi-user
  abstractions in V1.
- **Privacy boundary impact**: LinkedIn authentication and session use stay local-only;
  cloud stores neither credentials nor browser session state; cloud-side scraping is excluded.
- **Sync model impact**: Local agent pushes JSON deltas; cloud applies authenticated idempotent
  upserts to canonical storage; no database-file copy sync path is allowed.
- **Classification impact**: Taxonomy assignment, topic discovery, and label refinement are modeled
  as separate concerns; stable labeling remains the default path.
- **Cost/ops impact**: Core workflows operate without mandatory paid APIs and prioritize
  low-maintenance automation.
- **Persistence/backup impact**: Canonical persistence and backup are designed for safe live-database
  operation and restart durability.
- **Observability/reproducibility impact**: Sync diagnostics, run metadata,
  taxonomy version, and model configuration are tracked for reproducibility.

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: A manual sync run ingests and classifies at least 95% of newly saved posts in one pass,
  with failures surfaced in diagnostics.
- **SC-002**: 100% of matched known-topic posts receive stable-topic assignments above configured
  confidence threshold without manual intervention.
- **SC-003**: 100% of unmatched or low-confidence posts are routed to the review/discovery workflow
  within one discovery cycle.
- **SC-004**: User can complete review actions (approve, merge, reject, promote) for selected queue
  items in under 60 seconds per item.
- **SC-005**: Remote authenticated UI access is available from phone and desktop browser for
  library browsing, search, and notes.
- **SC-006**: Search returns results for title/content/summary/labels/notes queries with filters,
  and 90% of interactive searches return visible results within 2 seconds for datasets up to 50,000 posts.
- **SC-007**: Canonical persistence survives restart testing without losing committed post,
  topic, and note data.
- **SC-008**: Backup and restore drill can recover a consistent library snapshot without requiring
  database-file replacement during active operation.

## Assumptions

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right assumptions based on reasonable defaults
  chosen when the feature description did not specify certain details.
-->

- User operates the local sync agent on a machine where they already maintain a valid LinkedIn
  browser session.
- V1 supports browser-based remote access and does not include a native mobile app.
- LinkedIn saved-post availability and page structure remain sufficiently stable for local ingestion.
- User can provide initial stable taxonomy and adjust thresholds over time.
- Hosted environment can run authenticated UI, authenticated ingest API, canonical persistence,
  and automated backup/restart workflows within low-maintenance operational constraints.
