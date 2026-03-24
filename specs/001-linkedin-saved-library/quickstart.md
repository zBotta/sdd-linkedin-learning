# Quickstart: LinkedIn Saved Posts Knowledge Library (V1)

## 1. Prerequisites
- Python 3.11+
- Docker + Docker Compose
- Local browser with active LinkedIn session
- AWS EC2 instance with EBS volume attached

## 2. Configure Local Agent
1. Create local config for:
   - cloud API base URL
   - ingest auth token
   - taxonomy file path (`topics.yaml`)
   - assignment/discovery thresholds
2. Ensure Playwright browsers are installed.
3. Confirm local auth session is valid in the browser profile used by scraper.

## 3. Bootstrap Cloud Node
1. Provision EC2 instance and attach persistent EBS volume for SQLite DB path.
2. Run bootstrap (user-data script) to:
   - install Docker/Docker Compose
   - pull/build API and UI images
   - configure env vars from Parameter Store
   - start services with restart policies and healthchecks

## 4. Initialize Database
1. Run `scripts/init_db.py` once on cloud host.
2. Verify:
   - tables created (`posts`, `topics`, `post_topics`, `topic_runs`, `topic_candidates`, `notes`)
   - FTS5 indexes created
   - SQLite in WAL mode

## 5. Start Local-to-Cloud Flow
1. Run local sync agent.
2. Validate API accepts batch at `POST /ingest/batch`.
3. Verify `GET /sync-status` reflects latest run.
4. Open Streamlit UI and confirm new content appears without restart.

## 6. Run Discovery and Review
1. Trigger daily discovery job (or run manually for validation).
2. Inspect candidates with `GET /topic-candidates` and Review page.
3. Submit decisions via `POST /topic-candidates/{id}/decision`.
4. Use manual backlog reprocess action after promotions.

## 7. Backup and Recovery Check
1. Run `scripts/backup_db.py` using SQLite-safe backup mode.
2. Optionally trigger EBS snapshot after DB backup completes.
3. Perform restore drill in non-production environment.

## 8. Health Validation
- `GET /health` returns service and DB health.
- Docker healthchecks report healthy API and UI containers.
- Search works across title/content/summary/notes.
