from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path


class ValidationEvidenceWriter:
    def __init__(self, output_path: Path) -> None:
        self.output_path = output_path
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def append_record(
        self,
        *,
        run_id: str,
        check_type: str,
        status: str,
        payload: dict,
    ) -> dict:
        record = {
            "run_id": run_id,
            "check_type": check_type,
            "status": status,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        with self.output_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        return record
