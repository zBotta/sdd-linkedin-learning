from __future__ import annotations

from local_sync.preprocessing import normalize_post
from local_sync.topic_discovery import TopicDiscoveryPipeline
from shared.models import PostClassification, TopicMatch


def _post(source_post_id: str, title: str, content: str, saved_at: str):
    return normalize_post(
        {
            "source_post_id": source_post_id,
            "title": title,
            "content": content,
            "saved_at": saved_at,
        }
    )


def test_discovery_scope_includes_unmatched_and_low_confidence_and_recent() -> None:
    posts = [
        _post("1", "Rust async", "cargo ownership", "2026-03-24T10:00:00+00:00"),
        _post("2", "MCP server", "tool protocol", "2026-03-24T10:10:00+00:00"),
        _post("3", "Gardening notes", "plants and soil", "2026-03-24T10:20:00+00:00"),
    ]

    classifications = [
        PostClassification(
            source_key=posts[0].source_key,
            taxonomy_version="v1",
            matches=[TopicMatch(topic_slug="rust", topic_name="Rust", confidence=0.8, role="primary")],
        ),
        PostClassification(
            source_key=posts[1].source_key,
            taxonomy_version="v1",
            matches=[TopicMatch(topic_slug="mcp", topic_name="MCP", confidence=0.2, role="primary")],
        ),
    ]

    pipeline = TopicDiscoveryPipeline(low_confidence_threshold=0.45, recent_window_days=365)
    scope = pipeline.select_scope(posts, classifications)

    assert [item.source_post_id for item in scope["unmatched"]] == ["3"]
    assert [item.source_post_id for item in scope["low_confidence"]] == ["2"]
    assert sorted(item.source_post_id for item in scope["recent"]) == ["1", "2", "3"]
