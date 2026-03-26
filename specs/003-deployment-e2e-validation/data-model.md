# Data Model: Phase 6 Deployment and End-to-End Validation

## Entity: ValidationRun
- Purpose: Top-level record for one deployment validation execution.
- Fields:
  - `run_id`
  - `started_at`
  - `finished_at`
  - `overall_status` (`passed|failed|partial`)
  - `mode` (`incremental_then_full_rescrape|incremental_only`)
  - `summary`
- Validation rules:
  - `overall_status=passed` requires all mandatory checks passed.

## Entity: DeploymentCheck
- Purpose: Record build/start outcome for deployment workflow.
- Fields:
  - `run_id`
  - `step_name`
  - `command`
  - `exit_code`
  - `status`
  - `timestamp`
- Validation rules:
  - build/start command must complete successfully.

## Entity: ReadinessCheck
- Purpose: Verify required services are reachable and healthy.
- Fields:
  - `run_id`
  - `service_name`
  - `probe`
  - `attempts`
  - `max_window_seconds` (300)
  - `status`
  - `last_observed_detail`
- Validation rules:
  - required services must be ready within 300 seconds.

## Entity: E2EFlowResult
- Purpose: Capture local-to-cloud processing evidence.
- Fields:
  - `run_id`
  - `scraped_count`
  - `new_count`
  - `processed_count`
  - `classification_run_id`
  - `discovery_run_id`
  - `push_applied`
  - `status`
- Validation rules:
  - if incremental `new_count=0`, rerun in full-rescrape mode and require `processed_count>=1`.
  - successful e2e validation requires `push_applied=true`.

## Entity: SQLVerificationResult
- Purpose: Persist strict table verification outcomes.
- Fields:
  - `run_id`
  - `table_name`
  - `expected_min_updates`
  - `observed_updates`
  - `required_for_pass`
  - `status`
- Validation rules:
  - required tables: `posts`, `post_topics`, `topic_runs`.
  - `topic_candidates` required only when candidates were emitted.
  - any required-table failure causes run failure.

## Entity: EmbeddingReliabilityResult
- Purpose: Validate discovery embedding path behavior.
- Fields:
  - `run_id`
  - `online_path_status`
  - `local_fallback_status`
  - `fallback_path_valid`
  - `error_detail`
  - `status`
- Validation rules:
  - pass if online path succeeds OR local fallback path is validated usable.
  - fail if both online and fallback paths are unavailable.
  - invalid fallback path must produce explicit validation error detail.

## Entity: ValidationEvidence
- Purpose: Standardized evidence payload for each check.
- Fields:
  - `run_id`
  - `check_type`
  - `raw_output_excerpt`
  - `recorded_at`
- Validation rules:
  - each mandatory check must emit at least one evidence record.

## State Transitions
1. `ValidationRun` starts in `running` state.
2. Execute deployment and readiness checks.
3. Execute E2E flow check.
4. Execute SQL verification checks.
5. Execute embedding reliability checks.
6. Final status:
   - `passed` if all mandatory checks pass.
   - `failed` if any mandatory check fails.
   - `partial` only when optional checks fail but mandatory checks pass.
