from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from cloud.api.main import create_app
from cloud.ui.data_access import UILibraryRepository
from shared.db import Database


def _headers() -> dict[str, str]:
    return {"Authorization": "Bearer test-token"}


def test_quickstart_ingest_to_ui_review(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "library.db"
    monkeypatch.setenv("CLOUD_DB_PATH", str(db_path))
    monkeypatch.setenv("INGEST_API_TOKEN", "test-token")

    app = create_app()

    payload = {
        "batchId": "quickstart-1",
        "sentAt": datetime.now(timezone.utc).isoformat(),
        "source": "local_sync",
        "posts": [
            {
                "source": "linkedin_saved",
                "sourcePostId": "qs-1",
                "savedAt": datetime.now(timezone.utc).isoformat(),
                "content": "A practical post about python agent workflows",
                "contentHash": "qs-hash-1",
                "title": "Python Agent Workflows",
                "metadataJson": {"kind": "article"},
                "status": "new",
            }
        ],
        "topics": [
            {
                "slug": "python",
                "name": "Python",
                "taxonomyVersion": "v1",
            }
        ],
        "postTopics": [
            {
                "postSource": "linkedin_saved",
                "postSourceId": "qs-1",
                "topicSlug": "python",
                "role": "primary",
                "confidence": 0.42,
                "assignmentSource": "taxonomy_assignment",
                "reviewState": "pending",
            }
        ],
        "topicCandidates": [
            {
                "id": "qs-cand-1",
                "label": "agent orchestration",
                "keywords": ["agent", "orchestration"],
                "evidenceCount": 2,
                "confidence": 0.61,
                "state": "pending",
            }
        ],
        "notes": [
            {
                "id": "qs-note-1",
                "postSource": "linkedin_saved",
                "postSourceId": "qs-1",
                "body": "initial note",
            }
        ],
    }

    with TestClient(app) as client:
        ingest = client.post("/ingest/batch", json=payload, headers=_headers())
        assert ingest.status_code == 200
        assert ingest.json()["applied"] is True

    repo = UILibraryRepository(Database(db_path))

    inbox = repo.inbox_posts(limit=10)
    assert [row["source_post_id"] for row in inbox] == ["qs-1"]

    search_rows = repo.search_posts(query="python", topic="python", status="new", source="linkedin_saved", limit=10)
    assert [row["source_post_id"] for row in search_rows] == ["qs-1"]

    candidates = repo.review_candidates()
    assert [row["id"] for row in candidates] == ["qs-cand-1"]

    low_conf = repo.review_low_confidence(threshold=0.5)
    assert [row["source_post_id"] for row in low_conf] == ["qs-1"]

    repo.apply_assignment_action("linkedin_saved", "qs-1", action="approve")
    low_conf_after = repo.review_low_confidence(threshold=0.5)
    assert low_conf_after[0]["review_state"] == "accepted"

    # With a lower threshold, the approved item should no longer be queued.
    assert repo.review_low_confidence(threshold=0.4) == []
