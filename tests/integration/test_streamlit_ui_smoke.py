from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from streamlit.testing.v1 import AppTest

from shared.db import Database


def _seed_ui_data(db_path: Path) -> None:
    db = Database(db_path)
    db.initialize()
    now = datetime.now(timezone.utc).isoformat()

    with db.connection() as conn:
        conn.execute(
            """
            INSERT INTO ingest_batches (batch_id, sent_at, source, applied, processed, errors, started_at, finished_at)
            VALUES (?, ?, ?, 1, 1, 0, ?, ?)
            """,
            ("seed-batch", now, "local_sync", now, now),
        )
        conn.execute(
            """
            INSERT INTO topics (slug, taxonomy_version, name, description, source_type, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("python", "v1", "Python", "Python content", "stable", now),
        )
        conn.execute(
            """
            INSERT INTO posts (
              source, source_post_id, url, author, published_at, saved_at, title,
              content, content_hash, language, metadata_json, summary,
              importance_score, novelty_score, status, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "linkedin_saved",
                "post-1",
                "https://example.com/post-1",
                "alice",
                now,
                now,
                "Working with Python",
                "A post about Python workflows.",
                "hash-1",
                "en",
                "{}",
                "Python workflows",
                0.7,
                0.6,
                "new",
                now,
            ),
        )
        conn.execute(
            """
            INSERT INTO post_topics (
              post_source, post_source_id, topic_slug, role, confidence,
              assignment_source, review_state, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "linkedin_saved",
                "post-1",
                "python",
                "primary",
                0.91,
                "taxonomy_assignment",
                "accepted",
                now,
            ),
        )
        conn.execute(
            """
            INSERT INTO topic_candidates (
              id, label, keywords_json, evidence_count, confidence, state,
              merged_into_topic_slug, run_id, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "cand-1",
                "python agents",
                '["python", "agent"]',
                2,
                0.62,
                "pending",
                None,
                "run-1",
                now,
            ),
        )
        conn.execute(
            """
            INSERT INTO search_fts (source, source_post_id, title, content, summary, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "linkedin_saved",
                "post-1",
                "Working with Python",
                "A post about Python workflows.",
                "Python workflows",
                "",
            ),
        )
        conn.commit()


def test_streamlit_requires_auth(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "library.db"
    _seed_ui_data(db_path)
    monkeypatch.setenv("CLOUD_DB_PATH", str(db_path))
    monkeypatch.setenv("UI_ACCESS_PASSWORD", "ui-pass")

    app = AppTest.from_file("cloud/ui/app.py")
    app.run()

    assert any("Sign in" in item.value for item in app.info)


def test_streamlit_navigation_after_auth(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "library.db"
    _seed_ui_data(db_path)
    monkeypatch.setenv("CLOUD_DB_PATH", str(db_path))
    monkeypatch.setenv("UI_ACCESS_PASSWORD", "ui-pass")

    app = AppTest.from_file("cloud/ui/app.py")
    app.session_state["ui_authenticated"] = True
    app.run()

    assert any(item.value == "Home" for item in app.header)

    app.sidebar.radio[0].set_value("Topics")
    app.run()
    assert any(item.value == "Topics" for item in app.header)

    app.sidebar.radio[0].set_value("Search")
    app.run()
    assert any(item.value == "Search" for item in app.header)
