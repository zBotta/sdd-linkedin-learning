# Data Model: Incremental Scrape Diff Reliability

## Entity: SyncCheckpoint

- Purpose: Durable local state used to decide whether a scraped post is new or already synced.
- Fields:
  - `seen_source_keys` (set/list of string): canonical identities already synced.
  - `last_run_at` (timestamp, nullable): latest completed run time.
  - `last_batch_id` (string, nullable): latest successful push batch id.
- Validation rules:
  - Keys are unique and non-empty.
  - Missing/invalid state initializes to empty-safe defaults.

## Entity: ScrapeRunMode

- Purpose: Defines scope behavior for each run.
- Values:
  - `incremental`: stop on first already-synced post.
  - `full_rescrape`: bypass early-stop and process full reachable scope.
- Validation rules:
  - Exactly one mode per run.
  - Mode must be recorded in run diagnostics.

## Entity: SyncRunResult

- Purpose: User-visible and testable summary of run behavior/outcome.
- Fields:
  - `batch_id` (string)
  - `full_rescrape` (bool)
  - `scraped_count` (int)
  - `new_count` (int)
  - `push_result` (object with `applied`, `status_code`, `message`)
- Validation rules:
  - Counts are non-negative.
  - `full_rescrape` must reflect effective mode used.

## Entity: PostIdentityRecord

- Purpose: Stable key used in checkpoint diffing.
- Fields:
  - `source` (string)
  - `source_post_id` (string)
  - `source_key` (derived `source:source_post_id`)
- Validation rules:
  - `source_post_id` required for normalization.
  - `source_key` must be deterministic across runs.

## State Transitions

1. Start run:
- Determine mode (`incremental` or `full_rescrape`).

2. Scrape + diff:
- In incremental mode, stop on first `source_key` found in checkpoint.
- In full-rescrape mode, ignore stop-on-seen rule.

3. Push success:
- Add newly pushed post keys to `seen_source_keys`.
- Update `last_batch_id` and `last_run_at`.

4. Push failure after retries:
- Do not add failed keys to `seen_source_keys`.
- Preserve retry eligibility for next run.
