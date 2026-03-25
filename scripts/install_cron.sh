#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/linkedin-library}"
DB_PATH="${DB_PATH:-/srv/linkedin-library/data/library.db}"
BACKUP_DIR="${BACKUP_DIR:-/srv/linkedin-library/backups}"
HEALTHCHECK_PATH="${HEALTHCHECK_PATH:-${APP_DIR}/scripts/healthcheck.sh}"
BACKUP_SCRIPT_PATH="${BACKUP_SCRIPT_PATH:-${APP_DIR}/scripts/backup_db.py}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
INGEST_API_TOKEN="${INGEST_API_TOKEN:-}"
CRON_FILE="/etc/cron.d/linkedin-library"

if [ -z "${INGEST_API_TOKEN}" ]; then
  echo "install_cron: INGEST_API_TOKEN is required" >&2
  exit 1
fi

mkdir -p "${BACKUP_DIR}"

cat > "${CRON_FILE}" <<EOF
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Daily backup at 02:15 UTC
15 2 * * * root ${PYTHON_BIN} ${BACKUP_SCRIPT_PATH} --db-path ${DB_PATH} --backup-dir ${BACKUP_DIR} --label library --keep 14 >> /var/log/linkedin-library-backup.log 2>&1

# Healthcheck every 5 minutes
*/5 * * * * root INGEST_API_TOKEN=${INGEST_API_TOKEN} ${HEALTHCHECK_PATH} >> /var/log/linkedin-library-healthcheck.log 2>&1
EOF

chmod 644 "${CRON_FILE}"

if command -v systemctl >/dev/null 2>&1; then
  systemctl restart cron 2>/dev/null || systemctl restart crond
fi

echo "install_cron: installed ${CRON_FILE}"
