# Quickstart: Validate Incremental Diff Reliability

## Prerequisites

- Local LinkedIn-authenticated browser profile available.
- Cloud API/UI stack already running.
- Environment file configured for sync execution.

## Configuration knobs

- `LINKEDIN_STOP_ON_FIRST_SEEN=true` enables incremental early-stop behavior.
- `LOCAL_SYNC_FULL_RESCRAPE=true` forces full backlog scan for one run.
- `LOCAL_EMBEDDING_MODEL_PATH` optionally points to a local embedding model for restricted networks.

## 1. Baseline incremental run

Run a sync in default mode (incremental expected):

```powershell
python -c "from local_sync.config import LocalSyncConfig; from local_sync.sync_agent import SyncAgent; import json; result=SyncAgent(LocalSyncConfig.from_env('cloud/.env')).run_once(limit=300); print(json.dumps(result, indent=2))"
```

Validate:

- `full_rescrape` is `false`.
- A second run with no new saves yields low `new_count` and avoids backlog behavior.

## 2. Full-rescan override check

Set override in env used by the run:

```dotenv
LOCAL_SYNC_FULL_RESCRAPE=true
```

Run sync again and validate:

- `full_rescrape` is `true`.
- Run does not stop at first already-synced item.

Restore default after validation:

```dotenv
LOCAL_SYNC_FULL_RESCRAPE=false
```

## 3. Push failure retry eligibility check

Simulate push failure (invalid API base URL or token) and run sync.

Validate:

- Push result indicates failure after up to 3 in-run retry attempts.
- Previously extracted unsent posts are retried on next run after connectivity/token fix.
- Successful retry run updates checkpoint state.

## 4. SSL/trust and local embedding fallback check

If BERTopic embedding-dependent logic is invoked and online model download is blocked by
enterprise TLS/proxy trust, configure either:

- trusted corporate CA/proxy settings for outbound Hugging Face access, or
- `LOCAL_EMBEDDING_MODEL_PATH` pointing to a readable local model.

Expected behavior:

- run fails fast with actionable error when embedding artifacts are required but unavailable.
- if `LOCAL_EMBEDDING_MODEL_PATH` is invalid/unreadable, run fails with explicit path validation error.

## 5. Regression checks

Run targeted integration tests:

```powershell
python -m pytest tests/integration/test_local_sync_prototype.py tests/integration/test_discovery_pipeline.py tests/integration/test_stable_classification.py
```

Expected:

- Existing sync behavior tests pass.
- New incremental/full-rescan semantics remain stable.

## Validation log

- Automated validation completed on 2026-03-25:
	- Command: `c:/Users/mbottari/Projects_local/sdd-linkedin-learning/.venv/Scripts/python.exe -m pytest tests/integration/test_local_sync_prototype.py tests/integration/test_discovery_pipeline.py tests/integration/test_stable_classification.py`
	- Result: `5 passed in 85.31s`
- Scenario validation completed on 2026-03-25 using deterministic injected local-sync harness (`.tmp_quickstart_validate.py`):
	- Baseline incremental behavior: PASS (`full_rescrape=false`, second run `new_count` did not increase)
	- Full-rescan override behavior: PASS (`full_rescrape=true`, `new_count == deduped_count`)
	- Push failure then recovery behavior: PASS (first run failed push, subsequent run retried unsynced payload and succeeded)
	- During harness run, SSL certificate warnings from Hugging Face were observed in this environment and did not bypass trust checks.
- Fallback path validation completed on 2026-03-25 (`.tmp_embedding_validate.py`):
	- Result: PASS (`ValueError` emitted with explicit invalid `LOCAL_EMBEDDING_MODEL_PATH` guidance)
- Manual LinkedIn UI/feed-order smoke execution remains optional and environment-dependent.
