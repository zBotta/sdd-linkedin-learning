# Research: LinkedIn Saved Posts Knowledge Library (V1)

## Decision 1: Hybrid local+cloud split with strict privacy boundary
- Decision: Keep LinkedIn authentication, scraping, normalization, and primary classification on the local machine; cloud handles ingest API, canonical DB, and hosted UI.
- Rationale: Satisfies privacy constraints and avoids cloud-side credential/session handling.
- Alternatives considered:
  - Full-cloud ingestion: rejected due to credential/session and scraping policy violations.
  - Full-local app only: rejected due to remote access and hosted-library requirement.

## Decision 2: Delta-sync with idempotent upserts (no DB-file sync)
- Decision: Local agent sends authenticated JSON deltas; FastAPI applies idempotent upserts to canonical SQLite.
- Rationale: Keeps Streamlit online, avoids dangerous SQLite file-copy replacement workflow, supports retries safely.
- Alternatives considered:
  - Copying SQLite files: rejected due to downtime, corruption risk, and governance conflict.

## Decision 3: SQLite as canonical DB with WAL + FTS5
- Decision: Use SQLite in WAL mode with FTS5 indexes over title/content/summary/notes.
- Rationale: Low-ops single-user persistence with acceptable read/write concurrency and built-in search.
- Alternatives considered:
  - Postgres: rejected for V1 due to increased operational overhead.
  - External search engine: rejected for V1 complexity and maintenance cost.

## Decision 4: BERTopic module separation is mandatory
- Decision: Separate three modules:
  - taxonomy_assignment
  - topic_discovery
  - topic_label_refinement
- Rationale: Preserves explainability and supports independent tuning without opaque coupling.
- Alternatives considered:
  - Single monolithic pipeline: rejected for maintainability and debugging limitations.

## Decision 5: Stable taxonomy assignment policy
- Decision: BERTopic zero-shot with `topics.yaml` as source of truth, configurable similarity threshold, one primary topic + optional secondary topics above stricter threshold.
- Rationale: Ensures stable labels while preserving useful multi-topic signals.
- Alternatives considered:
  - Single-topic only: rejected for losing valid multi-topic information.
  - Fully multi-label without hierarchy: rejected for noisy outcomes.

## Decision 6: Discovery cadence and scope
- Decision: Run discovery daily on unmatched posts, low-confidence posts, and rolling recent-window candidates.
- Rationale: Balances freshness and compute cost while catching drift and novel themes.
- Alternatives considered:
  - Discovery only on unmatched: rejected for missing low-confidence drift signals.
  - Continuous per-sync discovery: rejected for higher runtime overhead.

## Decision 7: Topic label refinement defaults
- Decision: Use BERTopic representation models (KeyBERTInspired, MaximalMarginalRelevance, LlamaCPP) for readable labels; LLM refinement is optional and non-blocking.
- Rationale: Better label quality without making ingestion dependent on local LLM availability.
- Alternatives considered:
  - Mandatory LLM refinement: rejected due to fragility and higher runtime.

## Decision 8: Local model defaults
- Decision:
  - Embeddings: `sentence-transformers/all-MiniLM-L6-v2`
  - Local GGUF model: `Llama-3.2-3B-Instruct-Q4_K_M`
- Rationale: Good quality-to-performance balance on commodity local hardware.
- Alternatives considered:
  - Larger models by default: rejected for higher memory/runtime costs in V1.

## Decision 9: API security model
- Decision: Require authentication on ingest and UI access; accept only authenticated JSON payloads from local agent.
- Rationale: Protects canonical data plane and remote access surface.
- Alternatives considered:
  - Unauthenticated local-network assumptions: rejected for insufficient security posture.

## Decision 10: Backup strategy for live SQLite
- Decision: Use SQLite-safe backup method (SQLite backup API or `VACUUM INTO` pattern on controlled schedule), with optional EBS snapshots for recovery points.
- Rationale: Avoids corruption risk from naive file copying and supports restore drills.
- Alternatives considered:
  - Raw file copy while live: rejected due to consistency risk.

## Decision 11: Deployment and operations
- Decision: EC2 target with Docker Compose, separate API and UI containers, EBS-backed persistence, healthchecks/restart policies, EC2 user-data bootstrap, config/secrets via AWS Systems Manager Parameter Store.
- Rationale: Minimal hosted footprint with reproducible deployment and low maintenance.
- Alternatives considered:
  - Multi-service managed architecture: rejected for V1 complexity and operational cost.

## Open Risks and Mitigations
- Risk: LinkedIn DOM changes break extraction.
  - Mitigation: Version selectors, fallback extraction routines, diagnostic logging.
- Risk: Classification thresholds degrade quality.
  - Mitigation: Store confidence and decision metadata; support review queue tuning.
- Risk: WAL growth or lock contention under long writes.
  - Mitigation: Short transactions, periodic checkpoints, monitoring.
- Risk: Manual backlog reprocess may be skipped.
  - Mitigation: Surface backlog age/count in Settings and Review pages.
