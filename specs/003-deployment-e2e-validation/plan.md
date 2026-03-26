# Implementation Plan: Phase 6 Deployment and End-to-End Validation

**Branch**: `003-deployment-e2e-validation` | **Date**: 2026-03-26 | **Spec**: `specs/003-deployment-e2e-validation/spec.md`
**Input**: Feature specification from `/specs/003-deployment-e2e-validation/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Add an executable deployment validation suite for Phase 6 that verifies container build/start health, local-to-cloud end-to-end processing, strict canonical SQL persistence checks, and BERTopic/embedding reliability behavior. The suite must be repeatable, bounded by explicit readiness and pass/fail rules, and produce structured evidence for operator review.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI, Streamlit, Playwright, BERTopic, sentence-transformers, Podman Compose, sqlite3  
**Storage**: Canonical cloud SQLite plus local sync checkpoint files  
**Testing**: pytest integration tests plus deployment/e2e smoke validations  
**Target Platform**: Local workstation (Windows/Linux/macOS) + containerized cloud runtime (Podman)  
**Project Type**: Hybrid local sync + cloud web application  
**Performance Goals**: service readiness within 5 minutes in >=95% of validation runs; standard validation execution <=20 minutes  
**Constraints**: single-user scope, local-only LinkedIn auth, no cloud scraping, no insecure TLS bypass, strict SQL pass/fail tables  
**Scale/Scope**: one user with recurring validation runs around deployments and regression checks

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Single-user scope: Feature introduces no multi-user roles, tenancy, or team abstractions.
- Privacy boundary: LinkedIn authentication/session handling remains local-only; no cloud credential/session storage; no cloud scraping behavior.
- Sync model: Data movement uses JSON deltas with idempotent cloud upserts; no SQLite file copy/replace sync path.
- Classification model: BERTopic-centered design keeps taxonomy_assignment, topic_discovery, and topic_label_refinement as separate concerns.
- Label stability: Stable taxonomy assignment remains default; discovery is secondary and promotion-driven.
- Cost/ops constraints: V1 has no required paid LLM/API dependency; architecture remains low-ops with minimal hosted footprint.
- Responsibility split: Local and cloud responsibilities are explicitly scoped and unchanged unless justified.
- Persistence safety: SQLite-safe backup and restore approach defined for live DB usage.
- Reproducibility/observability: Plan includes run metadata, sync diagnostics, classification metadata, and taxonomy/model version tracking.

Constitution gate status before research: PASS.

## Project Structure

### Documentation (this feature)

```text
specs/003-deployment-e2e-validation/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md
```

### Source Code (repository root)

```text
local_sync/
├── config.py
├── sync_agent.py
├── push_client.py
└── topic_discovery.py

cloud/
├── Dockerfile.api
├── Dockerfile.ui
├── docker-compose.yml
├── api/
└── ui/

shared/
└── schemas.py

tests/
├── integration/
└── contract/
```

**Structure Decision**: Use existing project layout and add deployment-validation documentation artifacts in `specs/003-deployment-e2e-validation`. Implementation is expected mainly in test, automation, and validation script/workflow paths.

## Phase 0: Research Plan

Research outputs in `specs/003-deployment-e2e-validation/research.md` resolve:

- Repeatable Podman deployment verification strategy
- Service readiness probing and bounded retry policy (5-minute window)
- E2E flow handling when incremental run has zero new posts (automatic full-rescrape validation)
- Strict SQL verification model for required registry tables (`posts`, `post_topics`, `topic_runs`) and conditional `topic_candidates`
- BERTopic/embedding reliability checks for trusted online path, local fallback path, and explicit failure mode
- Evidence collection format to support deterministic pass/fail reporting

## Phase 1: Design Plan

Design artifacts:

- `specs/003-deployment-e2e-validation/data-model.md`
- `specs/003-deployment-e2e-validation/contracts/deployment-validation.md`
- `specs/003-deployment-e2e-validation/quickstart.md`

Design scope:

- Define validation-run entities, evidence records, and pass/fail state transitions
- Define contract for mandatory vs optional checks and strict gating conditions
- Define executable quickstart commands and expected results for deployment, e2e, SQL, and embedding reliability

## Post-Design Constitution Check

- Single-user scope preserved: PASS.
- Local-first privacy boundary preserved: PASS.
- JSON delta ingest model preserved: PASS.
- BERTopic concern separation preserved: PASS.
- Stable-label-first policy unchanged: PASS.
- No paid API dependency introduced: PASS.
- Low-ops architecture preserved (Podman workflow): PASS.
- Safe persistence constraints preserved (no DB-file sync): PASS.
- Reproducibility strengthened with explicit validation evidence model: PASS.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
