from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from cloud.api.main import create_app


def _headers(token: str = "test-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_health_sync_status_and_ingest_contract(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CLOUD_DB_PATH", str(tmp_path / "library.db"))
    monkeypatch.setenv("INGEST_API_TOKEN", "test-token")
    app = create_app()

    with TestClient(app) as client:
        health = client.get("/health", headers=_headers())
        assert health.status_code == 200
        assert set(health.json().keys()) == {"status", "db", "timestamp"}

        sync = client.get("/sync-status", headers=_headers())
        assert sync.status_code == 200
        assert set(sync.json().keys()) == {
            "lastRunId",
            "status",
            "startedAt",
            "finishedAt",
            "processed",
            "errors",
        }

        payload = {
            "batchId": "batch-1",
            "sentAt": datetime.now(timezone.utc).isoformat(),
            "source": "local_sync",
            "posts": [
                {
                    "source": "linkedin_saved",
                    "sourcePostId": "p1",
                    "savedAt": datetime.now(timezone.utc).isoformat(),
                    "content": "hello world",
                    "contentHash": "abc123",
                    "title": "Post",
                    "metadataJson": {},
                }
            ],
            "topics": [
                {
                    "slug": "rust",
                    "name": "Rust",
                    "taxonomyVersion": "v1",
                }
            ],
            "postTopics": [
                {
                    "postSource": "linkedin_saved",
                    "postSourceId": "p1",
                    "topicSlug": "rust",
                    "role": "primary",
                    "confidence": 0.9,
                    "assignmentSource": "taxonomy_assignment",
                    "reviewState": "accepted",
                }
            ],
            "topicCandidates": [],
            "notes": [],
        }
        ingest = client.post("/ingest/batch", json=payload, headers=_headers())
        assert ingest.status_code == 200
        assert ingest.json()["batchId"] == "batch-1"
        assert ingest.json()["applied"] is True


def test_auth_and_validation_rejections(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CLOUD_DB_PATH", str(tmp_path / "library.db"))
    monkeypatch.setenv("INGEST_API_TOKEN", "test-token")
    app = create_app()

    with TestClient(app) as client:
        unauthorized = client.get("/health")
        assert unauthorized.status_code == 401

        invalid = client.post("/ingest/batch", json={"batchId": "x"}, headers=_headers())
        assert invalid.status_code == 422
