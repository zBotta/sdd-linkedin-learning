from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from cloud.api.main import create_app


def _headers() -> dict[str, str]:
    return {"Authorization": "Bearer test-token"}


def test_duplicate_batch_is_idempotent(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "library.db"
    monkeypatch.setenv("CLOUD_DB_PATH", str(db_path))
    monkeypatch.setenv("INGEST_API_TOKEN", "test-token")

    app = create_app()
    payload = {
        "batchId": "same-batch",
        "sentAt": datetime.now(timezone.utc).isoformat(),
        "source": "local_sync",
        "posts": [
            {
                "source": "linkedin_saved",
                "sourcePostId": "id-1",
                "savedAt": datetime.now(timezone.utc).isoformat(),
                "content": "hello idempotency",
                "contentHash": "hash-1",
            }
        ],
        "topics": [],
        "postTopics": [],
        "topicCandidates": [],
        "notes": [],
    }

    with TestClient(app) as client:
        first = client.post("/ingest/batch", json=payload, headers=_headers())
        second = client.post("/ingest/batch", json=payload, headers=_headers())

    assert first.status_code == 200
    assert first.json()["applied"] is True
    assert second.status_code == 200
    assert second.json()["applied"] is False

    with sqlite3.connect(db_path) as conn:
        post_count = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        batch_count = conn.execute("SELECT COUNT(*) FROM ingest_batches").fetchone()[0]
        fts_count = conn.execute("SELECT COUNT(*) FROM search_fts").fetchone()[0]

    assert post_count == 1
    assert batch_count == 1
    assert fts_count == 1
