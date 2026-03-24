from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from cloud.api.main import create_app


def _headers(token: str = "test-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _seed_candidate(client: TestClient) -> str:
    payload = {
        "batchId": "seed-1",
        "sentAt": datetime.now(timezone.utc).isoformat(),
        "source": "local_sync",
        "posts": [
            {
                "source": "linkedin_saved",
                "sourcePostId": "sp1",
                "savedAt": datetime.now(timezone.utc).isoformat(),
                "content": "candidate content",
                "contentHash": "seedhash",
            }
        ],
        "topics": [],
        "postTopics": [],
        "topicCandidates": [
            {
                "id": "cand-1",
                "label": "agent workflows",
                "keywords": ["agent", "workflow"],
                "evidenceCount": 2,
                "confidence": 0.62,
                "state": "pending",
            }
        ],
        "notes": [],
    }
    response = client.post("/ingest/batch", json=payload, headers=_headers())
    assert response.status_code == 200
    return "cand-1"


def test_topic_run_and_candidate_decision_contract(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CLOUD_DB_PATH", str(tmp_path / "library.db"))
    monkeypatch.setenv("INGEST_API_TOKEN", "test-token")
    app = create_app()

    with TestClient(app) as client:
        create_run = client.post(
            "/topic-runs",
            json={
                "runType": "discovery",
                "taxonomyVersion": "v1",
                "embeddingModel": "sentence-transformers/all-MiniLM-L6-v2",
                "status": "success",
                "startedAt": datetime.now(timezone.utc).isoformat(),
            },
            headers=_headers(),
        )
        assert create_run.status_code == 200
        assert "id" in create_run.json()

        candidate_id = _seed_candidate(client)

        list_candidates = client.get("/topic-candidates", headers=_headers())
        assert list_candidates.status_code == 200
        assert any(item["id"] == candidate_id for item in list_candidates.json())

        decided = client.post(
            f"/topic-candidates/{candidate_id}/decision",
            json={"decision": "promote"},
            headers=_headers(),
        )
        assert decided.status_code == 200
        assert decided.json()["state"] == "promoted"

        missing = client.post(
            "/topic-candidates/does-not-exist/decision",
            json={"decision": "reject"},
            headers=_headers(),
        )
        assert missing.status_code == 404
