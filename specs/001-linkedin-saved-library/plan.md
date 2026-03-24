# Implementation Plan: LinkedIn Saved Posts Knowledge Library (V1)

**Branch**: `001-linkedin-saved-library` | **Date**: 2026-03-24 | **Spec**: `/specs/001-linkedin-saved-library/spec.md`
**Input**: Feature specification from `/specs/001-linkedin-saved-library/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Build a single-user, low-ops knowledge library where a local Python agent performs
LinkedIn saved-post extraction and BERTopic-based classification, then pushes authenticated
JSON deltas to a cloud FastAPI ingest service that performs idempotent upserts into a canonical
SQLite database. A Streamlit UI remains online and reads the live database for search, browse,
review workflow, and notes. The system prioritizes privacy (local auth boundary), low recurring
cost (local inference and optional LLM refinement), and maintainability (modular boundaries).

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI, Streamlit, Playwright, BERTopic, sentence-transformers, UMAP, HDBSCAN, scikit-learn, sqlite3, pydantic  
**Storage**: Canonical SQLite (WAL mode) on EC2 EBS volume; SQLite FTS5 indexes for search  
**Testing**: pytest (unit/integration/contract), httpx for API tests, Playwright smoke validation for local extraction paths  
**Target Platform**: Local user machine (Windows/macOS/Linux) + AWS EC2 (Linux) cloud host
**Project Type**: Hybrid single-user system (local agent + cloud web-service + hosted UI)  
**Performance Goals**: 95% sync ingestion success per run; 90% interactive search responses <2s for up to 50k posts; UI remains online during ingest and backups  
**Constraints**: Local-only LinkedIn auth boundary; no cloud-side scraping; JSON delta sync only; no DB-file replacement sync; no required paid LLM/API; low-ops deployment and recovery  
**Scale/Scope**: One user, one canonical library, up to ~50k saved posts in V1 with daily sync/discovery cadence

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

Gate evaluation (pre-design): PASS

- No multi-user scope introduced.
- LinkedIn auth/session remains local-only.
- Delta push + idempotent upsert model enforced; no SQLite file shipping.
- BERTopic modules remain separated: taxonomy_assignment, topic_discovery,
  topic_label_refinement.
- Local models are default; paid APIs not required.
- Cloud footprint stays minimal: FastAPI + Streamlit + SQLite on one EC2 node.
- Backup strategy uses SQLite-safe mechanisms and optional EBS snapshots.

## Project Structure

### Documentation (this feature)

```text
specs/001-linkedin-saved-library/
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
repo/
├─ local_sync/
│  ├─ sync_agent.py
│  ├─ linkedin_scraper.py
│  ├─ preprocessing.py
│  ├─ taxonomy_assignment.py
│  ├─ topic_discovery.py
│  ├─ topic_label_refinement.py
│  ├─ state_store.py
│  ├─ push_client.py
│  └─ config.py
├─ cloud/
│  ├─ api/
│  │  ├─ main.py
│  │  ├─ routes/
│  │  ├─ services/
│  │  └─ auth.py
│  ├─ ui/
│  │  ├─ app.py
│  │  ├─ pages/
│  │  └─ components/
│  ├─ docker-compose.yml
│  ├─ Dockerfile.api
│  ├─ Dockerfile.ui
│  └─ bootstrap/
│     └─ ec2_user_data.sh
├─ shared/
│  ├─ db.py
│  ├─ models.py
│  ├─ schemas.py
│  ├─ taxonomy.py
│  └─ utils.py
├─ scripts/
│  ├─ init_db.py
│  ├─ backup_db.py
│  └─ healthcheck.sh
├─ tests/
│  ├─ contract/
│  ├─ integration/
│  └─ unit/
├─ topics.yaml
├─ pyproject.toml
└─ README.md
```

**Structure Decision**: Use a hybrid modular monorepo with explicit local/cloud/shared boundaries
to enforce privacy constraints and simplify low-ops deployment while preserving replaceability
for ingestion, classification, API, and UI modules.

## Phase Plan

### Phase 0: Research and Design Validation

- Validate BERTopic pipeline design for short-to-medium LinkedIn post text using small-batch
  assignment and daily discovery cadence.
- Define SQLite live-operation strategy (WAL, busy timeout, connection handling, backup mode).
- Confirm FastAPI auth approach and Streamlit auth/session model for single-user remote access.
- Confirm Playwright local-auth operating model and fallback behavior when session expires.
- Confirm EC2 bootstrap, Docker healthcheck, restart policy, and backup automation strategy.

Output artifacts:
- `/specs/001-linkedin-saved-library/research.md`

### Phase 1: Data and Contract Design

- Define canonical schema for posts/topics/post_topics/topic_runs/topic_candidates/notes.
- Define ingestion and review API contracts:
  - `POST /ingest/batch`
  - `GET /health`
  - `GET /sync-status`
  - `POST /topic-runs`
  - `GET /topic-candidates`
  - `POST /topic-candidates/{id}/decision`
- Define delta payload format and idempotency keys.
- Define FTS5 schema for title/content/summary/notes search.
- Define review actions and manual backlog reprocess trigger contract.

Output artifacts:
- `/specs/001-linkedin-saved-library/data-model.md`
- `/specs/001-linkedin-saved-library/contracts/ingest-api.yaml`
- `/specs/001-linkedin-saved-library/quickstart.md`

### Phase 2: Task Planning Readiness

- Confirm all constitution gates pass post-design.
- Confirm no unresolved critical decisions remain.
- Prepare detailed execution graph in `/speckit.tasks`.

## Data Flow and Module Boundaries

1. Local extraction: `linkedin_scraper.py` reads saved posts via local authenticated browser session.
2. Preprocessing: `preprocessing.py` normalizes content and deduplicates by source/content hash.
3. Classification:
   - `taxonomy_assignment.py`: BERTopic zero-shot with `topics.yaml` + configurable similarity.
   - `topic_discovery.py`: daily run on unmatched/low-confidence/recent windows.
   - `topic_label_refinement.py`: representation models + optional local LLM naming.
4. Delta generation: `state_store.py` and `sync_agent.py` produce changed records only.
5. Secure push: `push_client.py` posts authenticated JSON deltas to cloud ingest API.
6. Cloud ingest: FastAPI validates payloads and applies idempotent upserts in SQLite.
7. Read path: Streamlit reads live SQLite DB (WAL mode) without restart during ingest.
8. Operations path: scheduled backup script performs SQLite-safe backup and optional EBS snapshot.

## Risk Mitigation

- Scraping fragility risk:
  - Keep selectors versioned and add fallback extraction paths.
  - Fail gracefully with sync diagnostics and retry guidance.
- Idempotency/data drift risk:
  - Use deterministic source keys and upsert strategy.
  - Persist sync checkpoints and run metadata.
- SQLite concurrency risk:
  - WAL mode, bounded write transactions, and periodic checkpoint strategy.
- Model quality/runtime risk:
  - Keep assignment/discovery/refinement separated with tunable thresholds.
  - Make LLM refinement optional and non-blocking.
- Operational risk:
  - Docker healthchecks + restart policies.
  - Bootstrap automation via EC2 user data.
  - Backup verification and restore drill procedure.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

Post-design constitution re-check: PASS
