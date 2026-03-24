from __future__ import annotations

import json
from pathlib import Path

from local_sync.config import LocalSyncConfig
from local_sync.preprocessing import normalize_post
from local_sync.sync_agent import SyncAgent
from local_sync.topic_discovery import TopicDiscoveryPipeline
from shared.models import PostClassification, TopicMatch
from shared.schemas import PushResult


def _posts() -> list:
    return [
        normalize_post(
            {
                "source_post_id": "1",
                "title": "Agent orchestration",
                "content": "agent planning orchestration state machine",
                "saved_at": "2026-03-24T10:00:00+00:00",
            }
        ),
        normalize_post(
            {
                "source_post_id": "2",
                "title": "Agent workflow",
                "content": "agent workflow planning memory",
                "saved_at": "2026-03-24T10:05:00+00:00",
            }
        ),
        normalize_post(
            {
                "source_post_id": "3",
                "title": "Gardening",
                "content": "flowers and watering schedule",
                "saved_at": "2026-03-24T10:10:00+00:00",
            }
        ),
    ]


def test_discovery_generates_candidates_and_persists_run_metadata(tmp_path: Path) -> None:
    posts = _posts()
    classifications = [
        PostClassification(
            source_key=posts[2].source_key,
            taxonomy_version="v1",
            matches=[TopicMatch(topic_slug="other", topic_name="Other", confidence=0.9, role="primary")],
        )
    ]

    pipeline = TopicDiscoveryPipeline(low_confidence_threshold=0.5, recent_window_days=365)
    candidates, run = pipeline.discover(posts, classifications, taxonomy_version="v1")

    run_path = tmp_path / "state" / "discovery_runs.jsonl"
    candidates_path = tmp_path / "state" / "topic_candidates.jsonl"
    pipeline.persist(candidates, run, run_path, candidates_path)

    assert run.status == "success"
    assert run.input_count >= 2

    assert run_path.exists()
    lines = run_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    parsed_run = json.loads(lines[0])
    assert parsed_run["run_id"] == run.run_id

    assert candidates_path.exists()
    stored_candidates = [json.loads(line) for line in candidates_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(stored_candidates) == len(candidates)


def test_discovery_module_boundary_does_not_require_taxonomy_assignment_objects() -> None:
    posts = _posts()
    classifications: list[PostClassification] = []

    pipeline = TopicDiscoveryPipeline()
    candidates, run = pipeline.discover(posts, classifications, taxonomy_version="v1")

    assert run.status == "success"
    assert isinstance(candidates, list)


class FakeScraper:
    def __init__(self, posts: list) -> None:
        self._posts = posts

    def fetch_saved_posts(self, limit: int = 100) -> list[dict]:
        _ = limit
        return [
            {
                "source_post_id": post.source_post_id,
                "title": post.title,
                "content": post.content,
                "saved_at": post.saved_at.isoformat(),
            }
            for post in self._posts
        ]


class CapturePushClient:
    def __init__(self) -> None:
        self.payload: dict | None = None

    def build_payload(self, posts, post_topics=None, topic_candidates=None, metadata=None) -> dict:
        self.payload = {
            "posts": [item.model_dump(mode="json") for item in posts],
            "post_topics": post_topics or [],
            "topic_candidates": topic_candidates or [],
            "metadata": metadata or {},
        }
        return self.payload

    def push_payload(self, payload: dict):
        self.payload = payload
        return PushResult(applied=True, dry_run=True)


def test_manual_reprocess_is_explicit_and_discovery_delta_is_exported(tmp_path: Path) -> None:
    posts = _posts()
    taxonomy_path = tmp_path / "topics.yaml"
    taxonomy_path.write_text(
        """
taxonomy_version: v1.0.0
zeroshot_min_similarity: 0.3
secondary_min_similarity: 0.5
topics:
  - slug: rust
    name: Rust
    keywords: [rust, cargo, ownership]
  - slug: mcp
    name: MCP
    keywords: [mcp, server, tool]
""".strip(),
        encoding="utf-8",
    )

    push_client = CapturePushClient()
    config = LocalSyncConfig(
        state_path=tmp_path / "state" / "sync_state.json",
        export_dir=tmp_path / "exports",
        export_enabled=True,
        linkedin_profile_dir=tmp_path / "profile",
        linkedin_headless=False,
        linkedin_session_wait_seconds=30,
        push_enabled=False,
        cloud_api_base_url="",
        cloud_ingest_token="",
        push_timeout_seconds=5,
        taxonomy_path=taxonomy_path,
        discovery_runs_path=tmp_path / "state" / "discovery_runs.jsonl",
        discovery_candidates_path=tmp_path / "state" / "topic_candidates.jsonl",
        classification_runs_path=tmp_path / "state" / "classification_runs.jsonl",
    )
    agent = SyncAgent(config=config, scraper=FakeScraper(posts), push_client=push_client)

    cycle = agent.run_once(limit=100)
    assert cycle["discovery_run_id"]
    assert "discovery_candidate_count" in cycle

    export_payload = json.loads(Path(str(cycle["export_path"])).read_text(encoding="utf-8"))
    assert "topicCandidates" in export_payload
    assert "discoveryPostTopics" in export_payload

    manual = agent.manual_reprocess_backlog(limit=100)
    assert manual["mode"] == "manual_reprocess"
    assert manual["reprocessed_count"] == len(posts)
