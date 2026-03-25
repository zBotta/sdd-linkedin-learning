# Implementation Plan: Incremental Scrape Diff Reliability

**Branch**: `002-fix-scrape-diff` | **Date**: 2026-03-25 | **Spec**: `specs/002-fix-scrape-diff/spec.md`
**Input**: Feature specification from `/specs/002-fix-scrape-diff/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Restore reliable incremental sync by making checkpoint-based diff behavior authoritative for normal runs, preserving retry-safe unsynced state on push failures, and keeping explicit full-rescan control for debugging/backfill. The approach keeps local-auth/cloud-ingest boundaries unchanged while hardening sync state semantics, diagnostics, and tests.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Playwright (local scraping), FastAPI (cloud ingest), Streamlit (UI), Pydantic, sqlite3  
**Storage**: Local checkpoint JSON file for sync state; canonical cloud SQLite for ingested data  
**Testing**: pytest (unit/integration/contract)  
**Target Platform**: Local Windows/Linux/macOS machine for sync; Linux container runtime for cloud services
**Project Type**: Hybrid local-sync + cloud web service/application  
**Performance Goals**: Incremental no-new-content runs avoid backlog processing in >=95% of runs; newly discovered posts processed successfully in >=95% of incremental runs  
**Constraints**: Single-user only; local LinkedIn auth boundary; idempotent JSON delta push; no cloud-side scraping; no DB-file sync  
**Scale/Scope**: Single user, up to tens of thousands of saved posts over time, daily repeated sync runs

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Single-user scope: Feature introduces no multi-user roles, tenancy, or team abstractions.
- Privacy boundary: LinkedIn authentication/session handling remains local-only; no cloud
  credential/session storage; no cloud scraping behavior.
- Sync model: Data movement uses JSON deltas with idempotent cloud upserts; no SQLite file
  copy/replace sync path.
- Classification model: BERTopic-centered design keeps taxonomy_assignment,
  topic_discovery, and topic_label_refinement as separate concerns.
- Label stability: Stable taxonomy assignment remains default; discovery is secondary and
  promotion-driven.
- Cost/ops constraints: V1 has no required paid LLM/API dependency; architecture remains
  low-ops with minimal hosted footprint.
- Responsibility split: Local and cloud responsibilities are explicitly scoped and
  unchanged unless justified.
- Persistence safety: SQLite-safe backup and restore approach defined for live DB usage.
- Reproducibility/observability: Plan includes run metadata, sync diagnostics,
  classification metadata, and taxonomy/model version tracking.

Constitution gate status before research: PASS.

## Project Structure

### Documentation (this feature)

```text
specs/002-fix-scrape-diff/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
local_sync/
├── linkedin_scraper.py
├── sync_agent.py
├── state_store.py
└── config.py

cloud/
├── api/
└── ui/

shared/
└── schemas.py

tests/
├── integration/
├── contract/
└── unit/

specs/002-fix-scrape-diff/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
```

**Structure Decision**: Keep the existing hybrid layout (`local_sync`, `cloud`, `shared`, `tests`) and scope changes to local sync state/diff paths plus associated tests and docs. No new top-level projects are required.

## Phase 0: Research Plan

Research outputs are documented in `specs/002-fix-scrape-diff/research.md` and resolve:

- Durable local checkpoint source of truth for incremental diff.
- Retry-safe checkpoint updates under partial/failed push outcomes.
- Full-rescan override semantics and reset-to-incremental behavior.
- Feed-ordering risk and mitigations without violating local/cloud boundaries.

## Phase 1: Design Plan

Design artifacts are:

- `specs/002-fix-scrape-diff/data-model.md`
- `specs/002-fix-scrape-diff/contracts/sync-behavior.md`
- `specs/002-fix-scrape-diff/quickstart.md`

Design scope:

- Define state model for checkpoint, run mode, and push outcome transitions.
- Define configuration/runtime contract for incremental and full-rescan modes.
- Define behavioral contract for retry handling and checkpoint mutation rules.
- Provide end-to-end validation steps for incremental, full-rescan, and failure-retry paths.

## Post-Design Constitution Check

- Single-user scope preserved: PASS.
- Local-first privacy boundary preserved: PASS.
- JSON delta ingest/idempotent cloud model preserved: PASS.
- BERTopic classification concerns remain separated: PASS.
- Stable-label-first policy unchanged: PASS.
- No new paid dependency requirement: PASS.
- Low-ops architecture preserved: PASS.
- Safe persistence/backup expectations unchanged: PASS.
- Reproducibility/observability expanded for sync diagnostics: PASS.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

## Implementation Reconciliation

- Mode control implemented via `LINKEDIN_STOP_ON_FIRST_SEEN` and `LOCAL_SYNC_FULL_RESCRAPE` with authoritative full-rescrape override.
- Checkpoint loading hardened for missing/corrupt state and normalized seen-key recovery.
- Push reliability includes bounded retry (3 attempts, exponential backoff) and checkpoint mutation only on successful push.
- Scraper supports checkpoint-aware early-stop with backward-compatible orchestrator fallback.
- Embedding behavior supports secure trust/proxy remediation and local fallback path (`LOCAL_EMBEDDING_MODEL_PATH`) with explicit validation errors.
- Automated targeted regression suite executed and passing (see `research.md` and `quickstart.md` validation logs).
