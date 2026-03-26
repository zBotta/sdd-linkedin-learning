from __future__ import annotations

import sqlite3
from pathlib import Path

from scripts import validate_phase6


def _create_tables(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE posts (id INTEGER PRIMARY KEY)")
        conn.execute("CREATE TABLE post_topics (id INTEGER PRIMARY KEY)")
        conn.execute("CREATE TABLE topic_runs (id INTEGER PRIMARY KEY)")
        conn.execute("CREATE TABLE topic_candidates (id INTEGER PRIMARY KEY)")
        conn.commit()


def test_sql_stage_enforces_required_tables_and_conditional_topic_candidates() -> None:
    db_path = Path("tests/integration/phase6_sql_test.db")
    if db_path.exists():
        db_path.unlink()

    try:
        _create_tables(db_path)
        with sqlite3.connect(db_path) as conn:
            conn.execute("INSERT INTO posts (id) VALUES (1)")
            conn.execute("INSERT INTO post_topics (id) VALUES (1)")
            conn.commit()

        stage_without_candidates = validate_phase6.run_sql_stage(
            db_path=db_path,
            topic_candidates_emitted=0,
            expected_minimums={
                "posts": 1,
                "post_topics": 1,
                "topic_runs": 1,
                "topic_candidates": 1,
            },
        )

        assert stage_without_candidates["status"] == "failed"
        assert "topic_runs" in stage_without_candidates["metadata"]["required_failures"]
        assert "topic_candidates" not in stage_without_candidates["metadata"]["required_failures"]

        stage_with_candidates = validate_phase6.run_sql_stage(
            db_path=db_path,
            topic_candidates_emitted=1,
            expected_minimums={
                "posts": 1,
                "post_topics": 1,
                "topic_runs": 1,
                "topic_candidates": 1,
            },
        )

        assert stage_with_candidates["status"] == "failed"
        assert "topic_candidates" in stage_with_candidates["metadata"]["required_failures"]
    finally:
        if db_path.exists():
            try:
                db_path.unlink()
            except PermissionError:
                pass


def test_sql_stage_handles_missing_db_without_crashing() -> None:
    db_path = Path("tests/integration/phase6_missing_sql_test.db")
    if db_path.exists():
        db_path.unlink()

    stage = validate_phase6.run_sql_stage(
        db_path=db_path,
        topic_candidates_emitted=0,
        expected_minimums={
            "posts": 1,
            "post_topics": 1,
            "topic_runs": 1,
            "topic_candidates": 1,
        },
    )

    assert stage["status"] == "failed"
    assert "error_detail" in stage["metadata"]
    assert "no such table" in stage["metadata"]["error_detail"].lower()

    if db_path.exists():
        try:
            db_path.unlink()
        except PermissionError:
            pass
