#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-http://localhost:8000/health}"
UI_URL="${UI_URL:-http://localhost:8501/_stcore/health}"
DB_PATH="${DB_PATH:-/srv/linkedin-library/data/library.db}"
INGEST_API_TOKEN="${INGEST_API_TOKEN:-}"

fail() {
  echo "healthcheck: $*" >&2
  exit 1
}

if [ -z "${INGEST_API_TOKEN}" ]; then
  fail "INGEST_API_TOKEN is not set"
fi

curl -fsS -H "Authorization: Bearer ${INGEST_API_TOKEN}" "${API_URL}" >/dev/null || fail "api health failed"
curl -fsS "${UI_URL}" >/dev/null || fail "ui health failed"

python - <<PY
import sqlite3
from pathlib import Path

path = Path("${DB_PATH}")
if not path.exists():
    raise SystemExit("database file missing")
with sqlite3.connect(path) as conn:
    conn.execute("SELECT 1").fetchone()
PY

echo "healthcheck: ok"
