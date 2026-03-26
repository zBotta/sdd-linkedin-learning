# Research: Phase 6 Deployment and End-to-End Validation

## Decision 1: Use Podman compose as the canonical deployment validation path
- Decision: Validate deployment by executing the same compose-based build/start workflow used in operations.
- Rationale: Captures Dockerfile and compose integration behavior together.
- Alternatives considered:
  - Per-image build checks only: rejected because service wiring and runtime config issues can be missed.

## Decision 2: Apply bounded readiness retries with a strict timeout
- Decision: Probe required services repeatedly for up to 5 minutes before declaring readiness failure.
- Rationale: Balances startup variability with deterministic failure behavior.
- Alternatives considered:
  - Immediate single probe: rejected as too flaky during normal startup.
  - Unbounded wait: rejected because it blocks automation and obscures failure states.

## Decision 3: Preserve end-to-end signal when incremental mode finds no new posts
- Decision: If incremental validation yields zero new posts, switch to full-rescrape validation and require at least one processed post.
- Rationale: Maintains true end-to-end verification without relying on fresh feed changes.
- Alternatives considered:
  - Failing immediately on zero new posts: rejected as high false-failure risk.
  - Skipping E2E assertions: rejected because it weakens deployment confidence.

## Decision 4: Enforce strict SQL persistence verification gates
- Decision: For pass/fail, require expected minimum updates in `posts`, `post_topics`, and `topic_runs` for the same run; require `topic_candidates` only when discovery emits candidates.
- Rationale: Ensures core data-plane integrity while handling valid no-candidate discovery outcomes.
- Alternatives considered:
  - Partial table checks: rejected because they can hide pipeline regressions.

## Decision 5: Validate embedding reliability with secure fallback rules
- Decision: Embedding reliability passes when either trusted online artifact resolution succeeds or local fallback is valid; fails when both paths are unavailable.
- Rationale: Supports enterprise network restrictions without insecure trust bypasses.
- Alternatives considered:
  - Online-only success criteria: rejected due to restricted-network environments.
  - Insecure TLS bypass for tests: rejected by security and constitution constraints.

## Decision 6: Record structured validation evidence for reproducibility
- Decision: Each validation step must record command/probe, timestamp, status, and concise result evidence.
- Rationale: Enables deterministic re-runs and operational debugging.
- Alternatives considered:
  - Unstructured narrative notes only: rejected due to inconsistent triage value.

## Decision 7: Keep deployment validations coupled with regression tests
- Decision: Run targeted integration tests as companion checks after deployment/e2e validations.
- Rationale: Captures behavioral regressions that deployment checks alone may miss.
- Alternatives considered:
  - Deployment-only verification: rejected as incomplete quality coverage.

## Regression Record (2026-03-26)

Command executed:
- `uv run python -m pytest tests/integration/test_phase6_deployment.py tests/integration/test_phase6_readiness.py tests/integration/test_phase6_e2e.py tests/integration/test_phase6_sql.py tests/integration/test_phase6_embedding.py --basetemp tests/integration/.pytest-temp`

Result:
- Passed: 7
- Failed: 0
- Warnings: 1 (`.pytest_cache` permission warning; non-blocking)

## Full Runner Execution Record (2026-03-26)

Command path:
- Executed `run_validation(...)` with `include_us2=True` and `include_us3=True` in a deterministic sample invocation (`run_id=phase6-sample`) to generate a full evidence block.

Outcome:
- Overall status: `passed`
- Stage statuses: deployment/readiness/e2e/sql/embedding all `passed`
- Evidence output: `tests/integration/phase6_evidence_test.jsonl`
