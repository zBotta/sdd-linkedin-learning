from __future__ import annotations

import os
from pathlib import Path

from shared.db import Database


def main() -> None:
    db_path = Path(os.getenv("CLOUD_DB_PATH", ".state/library.db"))
    db = Database(db_path)
    db.initialize()
    print(f"Initialized database at {db.path}")


if __name__ == "__main__":
    main()
