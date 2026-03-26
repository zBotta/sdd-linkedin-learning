# Deployment Guide

This guide describes clone-to-deploy commands for the Phase 6 validation workflow.

## Important Distinction

- `scripts/deploy_phase6.sh` and `scripts/deploy_phase6.ps1` are testing/validation entrypoints (Phase 6 checks and evidence output).
- `scripts/deploy_cloud_ec2.sh` is the real deployment entrypoint for EC2 API/UI runtime.

## Prerequisites

- Git
- Podman >= 5.0 with `podman compose` support (required)
- Python == 3.12.* (required)
- `uv` >= 0.4 (optional but recommended for environment/package management)

Recommended version checks:

```powershell
git --version
podman --version
podman compose version
uv run python --version
uv --version
```

If `podman compose version` fails on Windows, initialize/start Podman machine first:

```powershell
podman machine list
podman machine init
podman machine start
podman compose version
```

## Fresh Clone Setup

```bash
git clone <repo-url>
cd sdd-linkedin-learning
```

Create env files:

```bash
cp .env.example .env
cp cloud/.env.example cloud/.env
```

PowerShell equivalent:

```powershell
Copy-Item .env.example .env
Copy-Item cloud/.env.example cloud/.env
```

Update required values in `.env` and `cloud/.env`.

Important for local Windows/macOS runs:
- Set `DATA_DIR` in `cloud/.env` to a writable local path (example: `./.state/cloud-data`).
- Set `CLOUD_DB_PATH` in `cloud/.env` to `/data/library.db` so API/UI use the mounted data volume.
- Do not use Linux host paths like `/srv/linkedin-library/data` on local desktop environments.
- For restricted TLS/proxy environments, set `LOCAL_EMBEDDING_MODEL_PATH` to a local embedding artifact path.
  Example: `C:/Users/my_user/.models/all-MiniLM-L6-v2_model.safetensors`

## Cross-Platform Validation Scripts

- Shell: `scripts/deploy_phase6.sh`
- PowerShell: `scripts/deploy_phase6.ps1`

Both wrappers forward args directly to `scripts/validate_phase6.py`.
Wrappers execute via `uv run --no-sync python` to keep runtime resolution consistent with the project environment and avoid unexpected network sync during deployment checks.
Validation defaults are loaded from repository `.env` and `cloud/.env` (no extra flags required for those settings).

## Real Deployment on EC2 (API + UI)

Use this when you want to deploy the actual cloud runtime in an EC2 instance (not Phase 6 test validation):

```bash
chmod +x scripts/deploy_cloud_ec2.sh
./scripts/deploy_cloud_ec2.sh up
```

Lifecycle commands:

- `./scripts/deploy_cloud_ec2.sh up`: build + start API/UI
- `./scripts/deploy_cloud_ec2.sh restart`: rebuild/recreate API/UI
- `./scripts/deploy_cloud_ec2.sh ps`: show service status
- `./scripts/deploy_cloud_ec2.sh logs` or `./scripts/deploy_cloud_ec2.sh logs api`
- `./scripts/deploy_cloud_ec2.sh down`: stop/remove API/UI

The EC2 script uses `cloud/docker-compose.yml`, reads `cloud/.env`, and ensures `DATA_DIR` exists before startup.

## Run Deployment Validation

PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/deploy_phase6.ps1
```

Shell:

```bash
chmod +x scripts/deploy_phase6.sh
./scripts/deploy_phase6.sh
```

What this does (default mode):
- Runs **US1 only**: deployment build/start + readiness checks.
- It is the fastest safety gate and answers: "Did the platform come up correctly?"
- It does **not** run data-flow (US2) or embedding reliability (US3) checks.

## Include US2 and US3 Stages

PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/deploy_phase6.ps1 --include-us2 --include-us3
```

Shell:

```bash
./scripts/deploy_phase6.sh --include-us2 --include-us3
```

What this adds:
- `--include-us2`: runs end-to-end local->cloud validation + strict SQL table gating.
- `--include-us3`: runs embedding reliability validation (online-or-fallback rules).
- Optional for faster test runs: `--test-e2e-sample-limit 10` to cap US2 scraping/classification during validation tests.
- Optional for strict incremental-only tests: `--disable-e2e-full-rescrape-fallback` to avoid the second full-rescrape attempt when no new posts are found.
- Optional for bounded deterministic test ingestion: `--test-force-full-rescrape` to run one full-rescrape pass only (still capped by `--test-e2e-sample-limit`).

e.g.:
```powershell
.\scripts\deploy_phase6.ps1 --include-us2 --include-us3 --test-e2e-sample-limit 10 --disable-e2e-full-rescrape-fallback --test-force-full-rescrape

## Validation Modes (Why Split)

- **US1 (default)**: quick deploy smoke gate after infra/config changes.
- **US1 + US2**: confirms data actually flows and is persisted correctly.
- **US1 + US2 + US3**: full Phase 6 confidence run (deploy + data + model reliability).

Why not force everything every time:
- US2/US3 are slower and more environment-dependent (sample data, DB state, embedding/network conditions).
- US1 gives a fast fail signal for the most common release issue: services not coming up.
- Full run is still available in one command when needed.

Recommended for fresh users:
1. Run US1 first to confirm stack health.
2. Run full command (`--include-us2 --include-us3`) before release or after significant changes.

## Useful Options

- `--output <path>`: evidence JSONL output path
- `--readiness-timeout <seconds>`
- `--sql-db-path <path>`
- `--embedding-online-available true|false`
- `--embedding-fallback-path <path>`
- `--test-e2e-sample-limit <n>`: test-only override for US2 sample size (example: `10`)
- `--disable-e2e-full-rescrape-fallback`: keep US2 to one incremental pass only
- `--test-force-full-rescrape`: run one full-rescrape pass only (useful when incremental finds 0 new posts)
- `VALIDATION_COMPOSE_COMMAND`: override compose executable/subcommand (examples: `podman compose`, `podman-compose`)

## Inference-Only Debug

If you only want to debug local classification/discovery embedding behavior (without deployment/push/scrape), run:

```powershell
uv run --no-sync python scripts/run_inference_debug.py --limit 10 --print-candidates
```

Use `--input-export <path>` to target a specific exported batch JSON file.

## Post-Run Checks

- API health (requires token): `curl -H "Authorization: Bearer <INGEST_API_TOKEN>" http://localhost:8000/health`
- UI health: `curl http://localhost:8501/_stcore/health`
- Evidence file: path from run summary (`output_path`)

## Real Runtime Test Command

This command runs actual Podman build/start and live HTTP checks (not mocked):

```powershell
$env:RUN_REAL_DEPLOY_TESTS="1"
uv run python -m pytest tests/integration/test_phase6_real_runtime.py -s
```

What it validates:
- `podman compose -f cloud/docker-compose.yml up -d --build` succeeds.
- API health endpoint responds with auth token from `cloud/.env`.
- UI health endpoint responds.
- A real `local_sync.push_client.PushClient` POST to `/ingest/batch` is accepted.

## Notes

- No insecure TLS bypass should be introduced.
- `topic_candidates` SQL requirement is conditional on candidate emission.
- Embedding stage fails with explicit diagnostics when both online and fallback paths are unavailable.
