from __future__ import annotations

from local_sync.preprocessing import (
    build_content_hash,
    deduplicate_posts,
    make_source_key,
    normalize_post,
    normalize_text,
)


def test_normalize_text_collapses_whitespace() -> None:
    assert normalize_text("  hello\n\tworld  ") == "hello world"


def test_build_content_hash_is_stable_for_equivalent_text() -> None:
    one = build_content_hash("Hello   world", title="  Example ")
    two = build_content_hash("Hello world", title="Example")
    assert one == two


def test_normalize_post_builds_canonical_model() -> None:
    post = normalize_post(
        {
            "source": "linkedin_saved",
            "source_post_id": "abc123",
            "title": "  Title  ",
            "content": "Line 1\n\nLine 2",
            "saved_at": "2026-03-24T10:15:00+00:00",
            "metadata": {"likes": 7},
        }
    )
    assert post.title == "Title"
    assert post.content == "Line 1 Line 2"
    assert post.metadata_json["likes"] == 7


def test_deduplicate_posts_prefers_latest_by_source_key_and_hash() -> None:
    a = normalize_post(
        {
            "source_post_id": "id-1",
            "title": "same",
            "content": "same content",
            "saved_at": "2026-03-24T10:00:00+00:00",
        }
    )
    b = normalize_post(
        {
            "source_post_id": "id-1",
            "title": "same",
            "content": "same content",
            "saved_at": "2026-03-24T12:00:00+00:00",
        }
    )
    c = normalize_post(
        {
            "source_post_id": "id-2",
            "title": "same",
            "content": "same content",
            "saved_at": "2026-03-24T11:00:00+00:00",
        }
    )

    deduped = deduplicate_posts([a, b, c])
    assert len(deduped) == 1
    assert deduped[0].source_post_id == "id-1"
    assert deduped[0].saved_at.isoformat() == "2026-03-24T12:00:00+00:00"


def test_make_source_key() -> None:
    assert make_source_key("linkedin_saved", "42") == "linkedin_saved:42"
