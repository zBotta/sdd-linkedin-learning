# Quickstart: Phase 6 Deployment and End-to-End Validation

## Prerequisites

- Python 3.12
- Podman with compose support
- `.env` configured from `.env.example`
- `cloud/.env` configured for API/UI runtime

## 1. Run US1-only validation (deployment + readiness)

From repository root:

```powershell
uv run python scripts/validate_phase6.py
```

Expected:
- Deployment stage and readiness stage run.
- Summary JSON is printed.
- Evidence is appended to `VALIDATION_RUN_OUTPUT_PATH`.

## 2. Include US2 (E2E + SQL)

```powershell
uv run python scripts/validate_phase6.py --include-us2
```

US2 behavior:
- E2E falls back from incremental to full-rescrape when `new_count=0`.
- SQL enforces required tables `posts`, `post_topics`, `topic_runs`.
- `topic_candidates` is required only when discovery emitted candidates.

## 3. Include US3 (embedding reliability)

```powershell
uv run python scripts/validate_phase6.py --include-us3 --embedding-online-available false --embedding-fallback-path C:/models/all-MiniLM-L6-v2
```

US3 pass/fail:
- Pass if online path succeeds OR fallback path is valid.
- Fail if both are unavailable.
- Invalid fallback path reports explicit path-aware error detail.

## 4. Full Phase 6 run (US1 + US2 + US3)

```powershell
uv run python scripts/validate_phase6.py --include-us2 --include-us3
```

## 5. Targeted regression suite

```powershell
uv run python -m pytest tests/integration/test_phase6_deployment.py tests/integration/test_phase6_readiness.py tests/integration/test_phase6_e2e.py tests/integration/test_phase6_sql.py tests/integration/test_phase6_embedding.py --basetemp tests/integration/.pytest-temp
```

## Sample Evidence Block

Sample generated from an executed full-phase runner invocation (`run_id=phase6-sample`):

```json
{"check_type":"deployment","payload":{"command":["podman-compose"],"exit_code":0,"stderr":"","stdout":"ok"},"recorded_at":"2026-03-26T09:23:06.730309+00:00","run_id":"phase6-sample","status":"passed"}
{"check_type":"readiness","payload":{"services":{"api":{"status":"passed"},"ui":{"status":"passed"}}},"recorded_at":"2026-03-26T09:23:06.732308+00:00","run_id":"phase6-sample","status":"passed"}
{"check_type":"e2e","payload":{"discovery_candidate_count":1,"mode":"incremental_then_full_rescrape","new_count":2,"processed_count":2,"push_applied":true,"scraped_count":7},"recorded_at":"2026-03-26T09:23:06.733308+00:00","run_id":"phase6-sample","status":"passed"}
```

