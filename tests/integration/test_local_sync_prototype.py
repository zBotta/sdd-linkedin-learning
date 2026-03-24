from __future__ import annotations

import json
from pathlib import Path

from local_sync.config import LocalSyncConfig
from local_sync.sync_agent import SyncAgent
from shared.schemas import PushResult


class FakeScraper:
    def fetch_saved_posts(self, limit: int = 100) -> list[dict]:
        _ = limit
        return [
            {
                "source_post_id": "p1",
                "title": "First",
                "content": "A short post",
                "saved_at": "2026-03-24T10:00:00+00:00",
            },
            {
                "source_post_id": "p1",
                "title": "First",
                "content": "A short post",
                "saved_at": "2026-03-24T11:00:00+00:00",
            },
            {
                "source_post_id": "p2",
                "title": "Second",
                "content": "Another post",
                "saved_at": "2026-03-24T12:00:00+00:00",
            },
        ]


class FakePushClient:
    def __init__(self) -> None:
        self.last_payload: dict | None = None

    def build_payload(self, posts: list) -> dict:
        return {"posts": [item.model_dump(mode="json") for item in posts]}

    def push_payload(self, payload: dict) -> PushResult:
        self.last_payload = payload
        return PushResult(applied=True, dry_run=True, message="fake")


def test_sync_agent_runs_one_cycle_and_exports_json(tmp_path: Path) -> None:
    state_path = tmp_path / "state" / "sync_state.json"
    export_dir = tmp_path / "exports"

    config = LocalSyncConfig(
        state_path=state_path,
        export_dir=export_dir,
        export_enabled=True,
        linkedin_profile_dir=tmp_path / "profile",
        linkedin_headless=False,
        linkedin_session_wait_seconds=30,
        push_enabled=False,
        cloud_api_base_url="",
        cloud_ingest_token="",
        push_timeout_seconds=5,
    )

    fake_push = FakePushClient()
    agent = SyncAgent(config=config, scraper=FakeScraper(), push_client=fake_push)

    result = agent.run_once(limit=10)

    assert result["scraped_count"] == 3
    assert result["deduped_count"] == 2
    assert result["new_count"] == 2

    assert result["export_path"] is not None
    export_path = Path(str(result["export_path"]))
    assert export_path.exists()

    exported = json.loads(export_path.read_text(encoding="utf-8"))
    assert len(exported["posts"]) == 2
    assert state_path.exists()

    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["last_batch_id"] == result["batch_id"]
    assert len(state["seen_source_keys"]) == 2

    assert fake_push.last_payload is not None
    assert len(fake_push.last_payload["posts"]) == 2
