from __future__ import annotations

from pathlib import Path

from cloud.ui.data_access import UILibraryRepository
from shared.db import Database


def _seed_repo(tmp_path: Path) -> UILibraryRepository:
    db_path = tmp_path / "library.db"
    db = Database(db_path)
    db.initialize()

    with db.connection() as conn:
        conn.execute(
            """
            INSERT INTO topics (slug, taxonomy_version, name, description, source_type, updated_at)
            VALUES (?, ?, ?, ?, ?, ?), (?, ?, ?, ?, ?, ?)
            """,
            (
                "python",
                "v1",
                "Python",
                "",
                "stable",
                "2026-01-01T00:00:00+00:00",
                "rust",
                "v1",
                "Rust",
                "",
                "stable",
                "2026-01-01T00:00:00+00:00",
            ),
        )

        posts = [
            (
                "linkedin_saved",
                "p1",
                "https://example.com/p1",
                "alice",
                "2026-01-01T08:00:00+00:00",
                "2026-01-01T10:00:00+00:00",
                "Python workflows",
                "workflow automation for python",
                "hash-p1",
                "en",
                "{}",
                "",
                0.9,
                0.6,
                "new",
                "2026-01-01T10:00:00+00:00",
            ),
            (
                "linkedin_saved",
                "p2",
                "https://example.com/p2",
                "bob",
                "2026-01-03T08:00:00+00:00",
                "2026-01-03T09:30:00+00:00",
                "Unassigned workflows",
                "workflow notes with no assignment",
                "hash-p2",
                "en",
                "{}",
                "",
                0.3,
                0.2,
                "archived",
                "2026-01-03T09:30:00+00:00",
            ),
            (
                "other_source",
                "p3",
                "https://example.com/p3",
                "carol",
                "2026-01-02T08:00:00+00:00",
                "2026-01-02T12:00:00+00:00",
                "Rust workflows",
                "workflow automation for rust",
                "hash-p3",
                "en",
                "{}",
                "",
                0.5,
                0.5,
                "review",
                "2026-01-02T12:00:00+00:00",
            ),
        ]

        conn.executemany(
            """
            INSERT INTO posts (
              source, source_post_id, url, author, published_at, saved_at, title,
              content, content_hash, language, metadata_json, summary,
              importance_score, novelty_score, status, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            posts,
        )

        conn.execute(
            """
            INSERT INTO post_topics (
              post_source, post_source_id, topic_slug, role, confidence,
              assignment_source, review_state, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?), (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "linkedin_saved",
                "p1",
                "python",
                "primary",
                0.91,
                "taxonomy_assignment",
                "accepted",
                "2026-01-01T10:05:00+00:00",
                "other_source",
                "p3",
                "rust",
                "primary",
                0.40,
                "taxonomy_assignment",
                "pending",
                "2026-01-02T12:05:00+00:00",
            ),
        )

        conn.execute(
            """
            INSERT INTO search_fts (source, source_post_id, title, content, summary, notes)
            VALUES (?, ?, ?, ?, ?, ?), (?, ?, ?, ?, ?, ?), (?, ?, ?, ?, ?, ?)
            """,
            (
                "linkedin_saved",
                "p1",
                "Python workflows",
                "workflow automation for python",
                "",
                "",
                "linkedin_saved",
                "p2",
                "Unassigned workflows",
                "workflow notes with no assignment",
                "",
                "",
                "other_source",
                "p3",
                "Rust workflows",
                "workflow automation for rust",
                "",
                "",
            ),
        )
        conn.commit()

    return UILibraryRepository(db)


def test_search_posts_filter_combo(tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path)

    rows = repo.search_posts(
        query="workflow",
        topic="python",
        status="new",
        source="linkedin_saved",
        min_confidence=0.8,
        limit=20,
    )

    assert [row["source_post_id"] for row in rows] == ["p1"]


def test_search_posts_date_bounds_day_precision(tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path)

    rows = repo.search_posts(
        query="workflow",
        date_from="2026-01-02",
        date_to="2026-01-03",
        limit=20,
    )

    assert {row["source_post_id"] for row in rows} == {"p2", "p3"}


def test_search_posts_min_confidence_excludes_null_topics(tmp_path: Path) -> None:
    repo = _seed_repo(tmp_path)

    rows = repo.search_posts(query="workflow", min_confidence=0.1, limit=20)

    assert {row["source_post_id"] for row in rows} == {"p1", "p3"}
    assert all(row["source_post_id"] != "p2" for row in rows)
