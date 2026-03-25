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


class SpyScraper:
    def __init__(self) -> None:
        self.last_seen_source_keys: set[str] | None = None
        self.last_stop_on_first_seen: bool | None = None

    def fetch_saved_posts(
        self,
        limit: int = 100,
        *,
        seen_source_keys: set[str] | None = None,
        stop_on_first_seen: bool = True,
    ) -> list[dict]:
        _ = limit
        self.last_seen_source_keys = set(seen_source_keys or set())
        self.last_stop_on_first_seen = stop_on_first_seen
        return [
            {
                "source_post_id": "new-1",
                "title": "New",
                "content": "Fresh post content",
                "saved_at": "2026-03-24T12:30:00+00:00",
            },
            {
                "source_post_id": "old-1",
                "title": "Old",
                "content": "Previously synced post",
                "saved_at": "2026-03-24T12:00:00+00:00",
            },
        ]


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


def test_sync_agent_passes_seen_keys_and_full_rescrape_override(tmp_path: Path) -> None:
    state_path = tmp_path / "state" / "sync_state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "seen_source_keys": ["linkedin_saved:old-1"],
                "last_run_at": None,
                "last_batch_id": None,
            }
        ),
        encoding="utf-8",
    )

    base_kwargs = {
        "state_path": state_path,
        "export_dir": tmp_path / "exports",
        "export_enabled": False,
        "linkedin_profile_dir": tmp_path / "profile",
        "linkedin_headless": False,
        "linkedin_session_wait_seconds": 30,
        "push_enabled": False,
        "cloud_api_base_url": "",
        "cloud_ingest_token": "",
        "push_timeout_seconds": 5,
    }

    push_1 = FakePushClient()
    scraper_1 = SpyScraper()
    normal_agent = SyncAgent(
        config=LocalSyncConfig(**base_kwargs),
        scraper=scraper_1,
        push_client=push_1,
    )
    normal_result = normal_agent.run_once(limit=10)

    assert scraper_1.last_seen_source_keys == {"linkedin_saved:old-1"}
    assert scraper_1.last_stop_on_first_seen is True
    assert normal_result["full_rescrape"] is False
    assert normal_result["new_count"] == 1
    assert push_1.last_payload is not None
    assert len(push_1.last_payload["posts"]) == 1

    push_2 = FakePushClient()
    scraper_2 = SpyScraper()
    full_agent = SyncAgent(
        config=LocalSyncConfig(**base_kwargs, full_rescrape=True),
        scraper=scraper_2,
        push_client=push_2,
    )
    full_result = full_agent.run_once(limit=10)

    assert scraper_2.last_seen_source_keys == set()
    assert scraper_2.last_stop_on_first_seen is False
    assert full_result["full_rescrape"] is True
    assert full_result["new_count"] == 2
    assert push_2.last_payload is not None
    assert len(push_2.last_payload["posts"]) == 2
