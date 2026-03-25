# Contract: Sync Behavior and Mode Semantics

## Purpose

Define observable behavior for incremental diff, full-rescan override, and retry-safe checkpoint updates.

## Configuration Inputs

- `LINKEDIN_STOP_ON_FIRST_SEEN` (bool, default `true`)
- `LOCAL_SYNC_FULL_RESCRAPE` (bool, default `false`)
- `LOCAL_EMBEDDING_MODEL_PATH` (optional local sentence-transformer path)

## Effective Mode Resolution

1. If `LOCAL_SYNC_FULL_RESCRAPE=true`, effective mode is `full_rescrape` and early-stop is disabled.
2. Otherwise effective mode is `incremental` and early-stop follows `LINKEDIN_STOP_ON_FIRST_SEEN`.

## Checkpoint Mutation Contract

- On push success:
  - New posts in payload are added to checkpoint seen keys.
  - Run metadata (`last_batch_id`, `last_run_at`) is updated.
- On push failure (after in-run retry policy):
  - Failed posts are not added to seen keys.
  - They remain eligible for retry on next run.

## Retry Contract

- In-run retry attempts: up to 3.
- Backoff policy: exponential delay between attempts.
- After max retries, run ends with failed push result and unsynced retry eligibility preserved.

## Embedding Availability Contract

- If embedding-dependent discovery logic is invoked and model artifacts are unavailable due
  SSL/certificate trust failures, run fails with actionable remediation guidance.
- Supported secure remediations are:
  - configure trusted enterprise CA/proxy settings
  - provide `LOCAL_EMBEDDING_MODEL_PATH` pointing to a readable local model path
- Insecure TLS verification bypass is not a supported behavior.
- If `LOCAL_EMBEDDING_MODEL_PATH` is configured but missing/unreadable, run fails with explicit
  path validation error.

## Observable Run Output Contract

Run summary includes:

- `full_rescrape` boolean
- counts (`scraped_count`, `new_count`)
- `push_result` with `applied` and status/message

## Non-goals

- No cloud-side scrape orchestration.
- No multi-user checkpoint partitioning.
- No DB-file replacement sync path.
