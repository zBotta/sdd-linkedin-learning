from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a SQLite-safe live backup using sqlite backup API.")
    parser.add_argument("--db-path", required=True, help="Path to live SQLite database file")
    parser.add_argument("--backup-dir", required=True, help="Directory to write backups into")
    parser.add_argument("--label", default="library", help="Backup file label prefix")
    parser.add_argument("--keep", type=int, default=14, help="Number of newest backups to keep")
    return parser.parse_args()


def run_integrity_check(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        value = conn.execute("PRAGMA integrity_check").fetchone()[0]
    if value != "ok":
        raise RuntimeError(f"backup integrity_check failed: {value}")


def prune_old_backups(backup_dir: Path, label: str, keep: int) -> None:
    backups = sorted(backup_dir.glob(f"{label}-*.sqlite"), reverse=True)
    for stale in backups[keep:]:
        stale.unlink(missing_ok=True)


def create_backup(db_path: Path, backup_dir: Path, label: str, keep: int) -> Path:
    if not db_path.exists():
        raise FileNotFoundError(f"database not found: {db_path}")

    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = backup_dir / f"{label}-{timestamp}.sqlite"
    temp_output = backup_dir / f".{label}-{timestamp}.tmp"

    with sqlite3.connect(db_path) as source:
        with sqlite3.connect(temp_output) as target:
            source.backup(target)

    run_integrity_check(temp_output)
    temp_output.replace(output)
    prune_old_backups(backup_dir, label, keep)
    return output


def main() -> None:
    args = parse_args()
    output = create_backup(
        db_path=Path(args.db_path),
        backup_dir=Path(args.backup_dir),
        label=args.label,
        keep=max(1, args.keep),
    )
    print(f"Backup created: {output}")


if __name__ == "__main__":
    main()
