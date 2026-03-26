# Contract: Deployment Validation Behavior (Phase 6)

## Purpose

Define pass/fail behavior, stage inclusion rules, and required evidence for `scripts/validate_phase6.py`.

## Command Surface

Primary entrypoint:
- `uv run python scripts/validate_phase6.py`

Story flags:
- `--include-us2`: include end-to-end and SQL stages.
- `--include-us3`: include embedding reliability stage.

Default behavior (no flags):
- Runs US1 mandatory stages only: deployment + readiness.

## Mandatory Validation Stages

1. Deployment stage
- Build/start services using the configured compose command.
- Failure fails the run.

2. Readiness stage
- Probe required services until ready or timeout.
- Timeout window: 5 minutes maximum by default.
- Any required service not ready by timeout fails the run.

3. End-to-end flow stage (`--include-us2`)
- Execute local-to-cloud processing validation.
- If incremental mode has zero new posts, rerun with full-rescrape in the same run.
- Requires at least one processed post and successful push application.

4. SQL verification stage (`--include-us2`)
- Required tables for pass/fail: `posts`, `post_topics`, `topic_runs`.
- `topic_candidates` is required only when discovery emitted one or more candidates.
- Any required-table failure fails the run.

5. Embedding reliability stage (`--include-us3`)
- Pass when trusted online embedding availability succeeds OR local fallback path is usable.
- Fail when both paths are unavailable.
- Invalid fallback path must emit explicit error detail that includes the configured path.

## Evidence Requirements

Each mandatory stage emits:
- check type
- timestamp
- status (`passed|failed`)
- stage payload/details

Evidence is appended to JSONL via `ValidationEvidenceWriter`.

## Run Outcome Rules

- PASS: all selected mandatory stages pass.
- FAIL: one or more selected mandatory stages fail.
- PARTIAL: reserved for future optional diagnostics (not used currently).

## Non-Goals

- No cloud-side LinkedIn scraping.
- No insecure TLS bypass.
- No DB-file replacement synchronization.
