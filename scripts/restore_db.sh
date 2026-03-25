#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <backup_file> <target_db_path> [--force]" >&2
  exit 1
fi


BACKUP_FILE="$1"
TARGET_DB_PATH="$2"
FORCE="${3:-}"

if [ ! -f "${BACKUP_FILE}" ]; then
  echo "restore: backup file not found: ${BACKUP_FILE}" >&2
  exit 1
fi

if [ -f "${TARGET_DB_PATH}" ] && [ "${FORCE}" != "--force" ]; then
  echo "restore: target exists (${TARGET_DB_PATH}), rerun with --force after stopping services" >&2
  exit 1
fi

python - <<PY
import sqlite3
from pathlib import Path

backup = Path("${BACKUP_FILE}")
result = None
with sqlite3.connect(backup) as conn:
    result = conn.execute("PRAGMA integrity_check").fetchone()[0]
if result != "ok":
    raise SystemExit(f"restore: backup integrity_check failed: {result}")
print("restore: backup integrity_check ok")
PY

mkdir -p "$(dirname "${TARGET_DB_PATH}")"
TMP_TARGET="${TARGET_DB_PATH}.restore.tmp"
cp -f "${BACKUP_FILE}" "${TMP_TARGET}"
mv -f "${TMP_TARGET}" "${TARGET_DB_PATH}"

echo "restore: restored ${BACKUP_FILE} -> ${TARGET_DB_PATH}"
