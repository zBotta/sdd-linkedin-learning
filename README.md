# sdd-linkedin-learning

Single-user personal knowledge library for LinkedIn Saved posts, implemented with a spec-driven workflow and optimized for low maintenance.

## What this project is

This project ingests your LinkedIn Saved posts, classifies them into stable learning topics, discovers emerging topics, and exposes a searchable web UI that you can access from desktop or mobile.

Primary objectives:

- keep LinkedIn authentication and scraping local
- keep cloud runtime simple and inexpensive
- provide broad remote access to your library through a hosted UI
- preserve privacy boundaries and reproducibility

## How it works

The system uses a hybrid architecture:

- Local machine:
	- reuses your local authenticated browser session
	- scrapes and normalizes saved posts
	- deduplicates and classifies content locally
	- sends authenticated JSON deltas to the cloud
- Cloud host:
	- runs an authenticated FastAPI ingest service
	- stores canonical SQLite data (WAL + FTS5)
	- runs Streamlit UI for remote browsing/search/review
	- performs backups and health checks

Important rule:

- no database file copy sync from local to cloud
- sync is delta-based and idempotent

## Local inference vs cloud access

The design intentionally splits concerns:

- local for inference and privacy:
	- BERTopic assignment/discovery and optional local LLM label refinement run on your machine
	- LinkedIn credentials/session data never go to cloud
- cloud for broad access and operations:
	- UI is always online for phone/work-browser access
	- API and DB provide canonical state and recoverability

This keeps sensitive extraction/classification local while still giving convenient remote access to results.

## Architecture summary

- local_sync: scraping, preprocessing, classification, push
- cloud/api: auth, ingest, idempotent upserts, review APIs
- cloud/ui: Home, Inbox, Topics, Search, Review, Settings
- shared: DB layer, schemas, models, taxonomy helpers
- scripts: init, healthcheck, backup, restore, scheduling

Classification modules remain separated:

- taxonomy_assignment
- topic_discovery
- topic_label_refinement

## Feature summary (V1)

- LinkedIn Saved post local sync
- local BERTopic-based stable taxonomy assignment
- discovery candidate generation for unmatched/low-confidence content
- review actions for low-confidence and candidate decisions
- notes and FTS-backed search over title/content/summary/notes
- authenticated ingest API and authenticated UI
- SQLite persistence with backup/restore automation

## Installation and first run (local machine)

This section walks through a first end-to-end run:

1. install dependencies
2. log in to LinkedIn from local Playwright session
3. run local classification with optional GGUF label refinement
4. push deltas to cloud API (which writes into SQLite)

### 1. Install prerequisites

- Python 3.11+
- Podman (for API + UI stack)
- local browser access for LinkedIn login

From repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
python -m playwright install chromium
```

Optional (for GGUF-based local refinement):

```powershell
pip install llama-cpp-python
```

### 2. Configure environment

Create local sync env file from template:

```powershell
Copy-Item .env.example .env
```

Minimum values for first cloud-connected run:

```dotenv
# Local sync
PUSH_ENABLED=true
CLOUD_API_BASE_URL=http://localhost:8000
CLOUD_INGEST_TOKEN=change-this-token
LINKEDIN_HEADLESS=false

# Optional GGUF refinement (leave empty to disable)
LLAMA_CPP_MODEL_PATH=C:/models/your-model.gguf
```

Notes:

- `CLOUD_INGEST_TOKEN` must match `INGEST_API_TOKEN` in `cloud/.env`.
- Keep `LINKEDIN_HEADLESS=false` for first login so you can complete auth manually.

### 3. Start cloud API + UI (Podman)

```powershell
cd cloud
podman compose --env-file .env up -d --build
cd ..
```

Verify API health:

```powershell
$token = (Get-Content cloud/.env | Select-String '^INGEST_API_TOKEN=').ToString().Split('=')[1]
Invoke-RestMethod -Headers @{ Authorization = "Bearer $token" } http://localhost:8000/health
```

### 4. First LinkedIn login and local sync/classification run

Run one sync cycle from repository root:

```powershell
python -c "from local_sync.config import LocalSyncConfig; from local_sync.sync_agent import SyncAgent; import json; result=SyncAgent(LocalSyncConfig.from_env()).run_once(limit=100); print(json.dumps(result, indent=2))"
```

Expected behavior:

- a Chromium window opens to LinkedIn Saved Posts
- if login is required, complete login/MFA in that browser
- return to terminal and press Enter when prompted
- normalization, dedup, classification, discovery, export, and push are executed

### 5. Verify data reached cloud SQLite

Check sync status:

```powershell
Invoke-RestMethod -Headers @{ Authorization = "Bearer $token" } http://localhost:8000/sync-status
```

Open UI:

- URL: `http://localhost:8501`
- sign in with `UI_ACCESS_PASSWORD` from `cloud/.env`
- verify posts appear in Home/Inbox/Search

### 6. Optional manual backlog reprocess

```powershell
python -c "from local_sync.config import LocalSyncConfig; from local_sync.sync_agent import SyncAgent; import json; result=SyncAgent(LocalSyncConfig.from_env()).manual_reprocess_backlog(limit=500); print(json.dumps(result, indent=2))"
```

### 7. Troubleshooting first run

- If push fails with auth error, confirm token parity between `.env` and `cloud/.env`.
- If push fails with connection error, verify API is running on port 8000.
- If zero posts are extracted, relaunch with `LINKEDIN_HEADLESS=false`, confirm LinkedIn Saved page access, and rerun.
- If GGUF refinement is not used, verify `LLAMA_CPP_MODEL_PATH` points to an existing `.gguf` and `llama-cpp-python` is installed.

## Deployment (Podman on local machine)

These commands run API + UI using Podman Compose.

### 1. Prerequisites

- Podman installed and running
- Podman compose provider available (`podman compose`)

Check:

```powershell
podman --version
podman compose version
```

### 2. Create runtime environment file

From repository root:

```powershell
Copy-Item cloud/.env.example cloud/.env
```

Edit `cloud/.env` and set:

- `INGEST_API_TOKEN`
- `UI_ACCESS_PASSWORD`
- `DATA_DIR` (for local dev, use a local persistent folder)

Example:

```dotenv
INGEST_API_TOKEN=change-this-token
UI_ACCESS_PASSWORD=change-this-password
CLOUD_DB_PATH=/data/library.db
API_PORT=8000
UI_PORT=8501
DATA_DIR=../.state/podman-data
```

### 3. Start services

```powershell
cd cloud
podman compose --env-file .env up -d --build
```

### 4. Validate runtime

```powershell
podman compose ps
podman compose logs -f api
podman compose logs -f ui
```

### 5. Check health endpoints

```powershell
$token = (Get-Content .env | Select-String '^INGEST_API_TOKEN=').ToString().Split('=')[1]
Invoke-RestMethod -Headers @{ Authorization = "Bearer $token" } http://localhost:8000/health
Invoke-WebRequest http://localhost:8501/_stcore/health
```

### 6. Backup and restore

From repository root, backup:

```powershell
python scripts/backup_db.py --db-path .state/podman-data/library.db --backup-dir .state/backups --label library --keep 14
```

Restore drill (stop services first):

```powershell
cd cloud
podman compose down
cd ..
bash scripts/restore_db.sh .state/backups/library-YYYYMMDDTHHMMSSZ.sqlite .state/podman-data/library.db --force
cd cloud
podman compose up -d
```

## Deployment on EC2

For EC2 bootstrap with Parameter Store integration, see:

- `cloud/bootstrap/ec2_user_data.sh`
- `docs/deployment.md`

## Governance

Engineering and product principles are defined in:

- `.specify/memory/constitution.md`

All specs, plans, tasks, and implementation changes must comply with the constitution.

## Spec Kit with Codex

After installing Spec Kit, initialize Codex-compatible skills:

```bash
specify init . --ai codex --ai-skills
```

