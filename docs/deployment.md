# Deployment and Recovery Runbook

## Scope

This runbook covers single-user V1 deployment on one EC2 instance using:

- Docker Compose for API and UI
- SQLite canonical database in a persistent EBS-backed directory
- AWS Systems Manager Parameter Store for runtime secrets/config
- Scheduled health checks and backups

No Postgres, Kubernetes, or multi-user controls are introduced.

## Prerequisites

1. EC2 instance with IAM permissions for Parameter Store read access:
   - `ssm:GetParameter`
   - `ssm:GetParameters`
2. Attached EBS volume intended for persistent app data.
3. Parameter Store keys populated:
   - `/linkedin-library/prod/INGEST_API_TOKEN` (SecureString)
   - `/linkedin-library/prod/UI_ACCESS_PASSWORD` (SecureString)
   - `/linkedin-library/prod/API_PORT` (String, optional)
   - `/linkedin-library/prod/UI_PORT` (String, optional)

## Bootstrap

Run user-data script at launch or manually:

```bash
bash cloud/bootstrap/ec2_user_data.sh
```

Recommended environment overrides before running:

```bash
export REPO_URL=https://github.com/<org>/<repo>.git
export REPO_REF=main
export AWS_REGION=us-east-1
export DATA_DEVICE=/dev/nvme1n1
```

What bootstrap does:

1. Installs Docker, AWS CLI, jq, and git.
2. Ensures Docker is enabled.
3. Formats/mounts EBS volume if needed.
4. Creates persistent data and backup directories.
5. Reads secrets/config from Parameter Store.
6. Writes `cloud/.env`.
7. Starts `docker compose up -d --build`.

## Runtime layout

- Compose file: `cloud/docker-compose.yml`
- API image: `cloud/Dockerfile.api`
- UI image: `cloud/Dockerfile.ui`
- DB path inside containers: `/data/library.db`
- Host persistent path: `${DATA_DIR}` (default `/srv/linkedin-library/data`)

## Health and restart behavior

- Service restarts: `restart: unless-stopped` for API and UI.
- API healthcheck: authenticated call to `/health`.
- UI healthcheck: `/_stcore/health`.
- Manual runtime check:

```bash
INGEST_API_TOKEN=<token> bash scripts/healthcheck.sh
```

## Backup

SQLite-safe live backup uses Python sqlite backup API:

```bash
python scripts/backup_db.py \
  --db-path /srv/linkedin-library/data/library.db \
  --backup-dir /srv/linkedin-library/backups \
  --label library \
  --keep 14
```

Backups are integrity-checked with `PRAGMA integrity_check`.

## Restore drill

1. Stop app services before replacing active DB:

```bash
cd cloud
docker compose down
```

2. Restore from a backup:

```bash
bash scripts/restore_db.sh /srv/linkedin-library/backups/library-YYYYMMDDTHHMMSSZ.sqlite /srv/linkedin-library/data/library.db --force
```

3. Start services and verify health:

```bash
cd cloud
docker compose up -d
INGEST_API_TOKEN=<token> bash ../scripts/healthcheck.sh
```

## Scheduled automation

Install cron-based backup + health checks:

```bash
sudo INGEST_API_TOKEN=<token> bash scripts/install_cron.sh
```

Default schedule:

- Backup daily at 02:15 UTC
- Healthcheck every 5 minutes

## Operations checklist

- On deploy: pull latest code, rebuild containers, run health check.
- Weekly: verify at least one fresh backup exists and run a restore drill to a temporary path.
- On incident: inspect `docker compose ps`, logs, healthcheck output, then restore latest known-good backup if needed.
