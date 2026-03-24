<!--
Sync Impact Report
- Version change: template (unversioned) -> 1.0.0
- Modified principles:
	- Template Principle 1 -> I. Single-User First
	- Template Principle 2 -> II. Local-First Privacy Boundary
	- Template Principle 3 -> III. Delta Sync, Not DB-File Sync
	- Template Principle 4 -> IV. BERTopic-Centered Classification
	- Template Principle 5 -> V. Stable Labels First, Discovery Second
	- Added VI. Local Inference Over Paid APIs
	- Added VII. Low-Ops Cloud Architecture
	- Added VIII. Clear Separation of Responsibilities
	- Added IX. Safe Persistence and Backup
	- Added X. Reviewable Automation
	- Added XI. Modularity and Replaceability
	- Added XII. Quality Expectations and Reproducibility
- Added sections:
	- System Boundaries and Required Architecture
	- Delivery Workflow and Quality Gates
- Removed sections:
	- None
- Templates requiring updates:
	- ✅ updated: .specify/templates/plan-template.md
	- ✅ updated: .specify/templates/spec-template.md
	- ✅ updated: .specify/templates/tasks-template.md
	- ⚠ pending: .specify/templates/commands/*.md (directory not present)
	- ✅ updated: README.md
- Deferred TODOs:
	- None
-->

# LinkedIn Saved Posts Knowledge Library Constitution

## Core Principles

### I. Single-User First
The system MUST be designed for exactly one user in V1. Implementations MUST NOT
introduce multi-user abstractions, roles, tenancy, team workspaces, or cross-account
permission models unless a future requirement explicitly mandates them.
Rationale: constraining scope keeps the architecture simple, cheaper, and faster to
operate while reducing accidental complexity.

### II. Local-First Privacy Boundary
LinkedIn authentication and session establishment MUST occur only on the local machine.
The cloud environment MUST NOT store LinkedIn credentials, cookies, or browser session
state, and cloud infrastructure MUST NOT perform LinkedIn scraping on behalf of users.
Rationale: privacy and account safety depend on a strict trust boundary.

### III. Delta Sync, Not DB-File Sync
Synchronization MUST use structured JSON deltas generated locally and sent to the cloud
ingest API. The cloud ingest layer MUST implement idempotent upserts, and the hosted UI
MUST read from the live canonical database. Copying or replacing a local SQLite file in
the cloud is prohibited.
Rationale: delta-based sync preserves online UI availability and avoids fragile file-level
database transfer patterns.

### IV. BERTopic-Centered Classification
Classification architecture MUST remain centered on BERTopic and MUST keep three concerns
explicitly separate: taxonomy_assignment, topic_discovery, and topic_label_refinement.
Implementations MUST NOT collapse these concerns into one opaque pipeline.
Rationale: separation improves explainability, controllability, and long-term evolution.

### V. Stable Labels First, Discovery Second
Stable taxonomy assignment MUST be the default classification path. Emerging-topic
discovery MUST be secondary and used to propose candidates for promotion into the stable
taxonomy. Known topic labels MUST remain consistent over time unless an explicit taxonomy
change is approved.
Rationale: consistency of known labels is required for reliable historical analysis.

### VI. Local Inference Over Paid APIs
The system MUST prefer local models and local inference wherever practical and MUST NOT
require paid LLM or API dependencies for V1 ingestion. Local LLM usage SHOULD remain
optional for basic ingestion and primarily support topic naming and label refinement.
Rationale: low recurring cost and offline-friendly operation are first-order constraints.

### VII. Low-Ops Cloud Architecture
Cloud architecture MUST use the smallest practical hosted footprint and prioritize simple,
inspectable components over distributed complexity. New services that materially increase
operational burden MUST NOT be introduced without documented necessity.
Rationale: low maintenance is a core product requirement, not an optimization.

### VIII. Clear Separation of Responsibilities
The local machine MUST own scraping, normalization, deduplication, classification, and
delta push responsibilities. The cloud MUST own authenticated ingest API handling,
canonical persistence, hosted UI serving, and backup operations.
Rationale: clean boundaries reduce security risk and simplify fault isolation.

### IX. Safe Persistence and Backup
SQLite MUST be treated as a live database, not a replaceable blob. Backup and restore
procedures MUST use SQLite-safe methods suitable for live workloads, and persistence
infrastructure MUST preserve data across EC2 restarts and failures.
Rationale: data durability and recoverability are non-negotiable for a knowledge library.

### X. Reviewable Automation
Automation MUST cover scheduled sync, local classification, cloud bootstrap, health
checks, restart handling, and backups. Automation MUST NOT attempt LinkedIn MFA or captcha
solving, credential recovery, or unsafe login behavior.
Rationale: automation must increase reliability without crossing security or account-risk
boundaries.

### XI. Modularity and Replaceability
Scraper, preprocessing, taxonomy assignment, discovery, label refinement, ingest API, UI,
and shared data model layers MUST remain modular and replaceable. Changes SHOULD preserve
future migration paths without requiring major rewrites.
Rationale: modularity prevents lock-in and enables incremental evolution.

### XII. Quality Expectations and Reproducibility
Code MUST be simple, readable, and testable. The platform MUST emit run metadata, sync
diagnostics, and classification metadata, and MUST record taxonomy versions and model
versions needed to reproduce prior outputs.
Rationale: maintainability and reproducibility are required for trust in system behavior.

## System Boundaries and Required Architecture

- Local-only LinkedIn auth boundary is mandatory.
- Cloud scraping is forbidden; cloud only ingests authenticated deltas.
- Live UI reads canonical cloud database state.
- Backups and restore drills MUST be documented and periodically validated.
- Platform choices MUST favor low recurring cost, low maintenance, and inspectability.

## Delivery Workflow and Quality Gates

- Every plan, spec, and task list MUST include an explicit constitution compliance check.
- Every feature affecting ingestion or classification MUST define observability outputs and
	reproducibility metadata changes.
- Every feature affecting storage or sync MUST define idempotency and backup impact.
- Any proposal that introduces multi-user scope, paid API dependency, or cloud-side scraping
	MUST be rejected unless constitution amendment is approved first.

## Governance

This constitution is the highest-priority engineering and product policy for this
repository. All plans, specs, tasks, and implementation changes MUST remain compliant.

Amendment procedure:
1. Submit a documented amendment proposal with rationale, impact analysis, and migration
	 implications.
2. Review constitution-template, plan-template, spec-template, tasks-template, command
	 docs, and runtime docs for required sync updates.
3. Approve and merge amendment plus all required template/runtime updates in one change.

Versioning policy:
- MAJOR: backward-incompatible governance changes, principle removals, or principle
	redefinitions.
- MINOR: new principle/section or materially expanded guidance.
- PATCH: wording clarifications, typo fixes, and non-semantic refinements.

Compliance review expectations:
- At planning time: pass constitution gates before research/design begins.
- At spec/task generation time: map requirements and tasks to relevant principles.
- At implementation/review time: verify no prohibited patterns were introduced, especially
	multi-user abstractions, cloud-side scraping, or DB-file sync.

**Version**: 1.0.0 | **Ratified**: 2026-03-24 | **Last Amended**: 2026-03-24
