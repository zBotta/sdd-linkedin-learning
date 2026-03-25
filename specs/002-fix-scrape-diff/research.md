# Research: Incremental Scrape Diff Reliability

## Decision 1: Checkpoint file remains source of truth for diff

- Decision: Use local checkpoint state (`seen_source_keys` + run metadata) as the authoritative diff source for incremental runs.
- Rationale: It is already durable, fast to query, independent from transient page structure, and aligned with existing idempotent push model.
- Alternatives considered:
  - Recompute diff from cloud DB on each run: rejected due to added coupling/network dependency.
  - Persist full scraped payload snapshots: rejected due to unnecessary size/privacy/complexity for V1.

## Decision 2: Checkpoint mutation occurs only after successful push

- Decision: Only mark posts as synced after push succeeds; failed pushes leave posts unsynced for automatic retry.
- Rationale: Prevents silent data loss and preserves at-least-once delivery semantics with cloud idempotency.
- Alternatives considered:
  - Mark synced before push: rejected due to dropped-data risk on transport failure.
  - Manual recovery queue only: rejected as too operationally heavy for single-user V1.

## Decision 3: Incremental mode default, full-rescan explicit override

- Decision: Keep incremental stop-on-first-seen enabled by default and provide explicit full-rescan mode for diagnostics/backfill.
- Rationale: Balances speed for routine runs with controlled full coverage when needed.
- Alternatives considered:
  - Always full-rescan: rejected due to poor run time.
  - No full-rescan option: rejected because debugging/reconciliation becomes difficult.

## Decision 4: Retry policy

- Decision: Retry failed delta pushes up to 3 times with exponential backoff in-run; if still failing, keep unsynced for next run.
- Rationale: Improves resilience without long indefinite blocking.
- Alternatives considered:
  - No retry: rejected due to avoidable transient failure impact.
  - Infinite retry loop: rejected due to run-time unpredictability.

## Decision 5: Feed-ordering anomalies

- Decision: Treat feed-order anomalies as acceptable risk in incremental mode; provide full-rescan mode as deterministic recovery path.
- Rationale: Maintains simple implementation while preserving correctness through explicit recovery operation.
- Alternatives considered:
  - Complex multi-window historical scanning every run: rejected due to complexity/performance cost.

## Regression Execution Notes (T025)

- Date: 2026-03-25
- Command: `c:/Users/mbottari/Projects_local/sdd-linkedin-learning/.venv/Scripts/python.exe -m pytest tests/integration/test_local_sync_prototype.py tests/integration/test_discovery_pipeline.py tests/integration/test_stable_classification.py`
- Result: PASS (`5 passed in 85.31s`)
- Environment note: invoking plain `pytest` failed in one interpreter due import path mismatch; running from configured workspace venv resolved execution and imports.
