from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from shared.db import Database


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class UILibraryRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def home_metrics(self) -> dict[str, object]:
        with self._db.connection() as conn:
            total_posts = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
            new_posts = conn.execute("SELECT COUNT(*) FROM posts WHERE status = 'new' OR status IS NULL").fetchone()[0]
            review_backlog = conn.execute(
                "SELECT COUNT(*) FROM post_topics WHERE review_state IN ('pending', 'edited') OR confidence < 0.5"
            ).fetchone()[0]
            candidate_count = conn.execute(
                "SELECT COUNT(*) FROM topic_candidates WHERE state = 'pending'"
            ).fetchone()[0]
            last_sync = conn.execute(
                "SELECT finished_at FROM ingest_batches ORDER BY finished_at DESC LIMIT 1"
            ).fetchone()

            topic_distribution_rows = conn.execute(
                """
                SELECT topic_slug, COUNT(*) AS count
                FROM post_topics
                WHERE role = 'primary'
                GROUP BY topic_slug
                ORDER BY count DESC
                LIMIT 8
                """
            ).fetchall()

        return {
            "total_posts": total_posts,
            "new_posts": new_posts,
            "review_backlog": review_backlog,
            "candidate_count": candidate_count,
            "last_sync": last_sync[0] if last_sync else None,
            "topic_distribution": [
                {"topic": row["topic_slug"], "count": row["count"]} for row in topic_distribution_rows
            ],
        }

    def inbox_posts(self, limit: int = 50) -> list[dict[str, object]]:
        with self._db.connection() as conn:
            rows = conn.execute(
                """
                SELECT
                  p.source,
                  p.source_post_id,
                                    p.url,
                  p.title,
                  p.saved_at,
                  p.content,
                  pt.topic_slug,
                  pt.confidence,
                  pt.review_state
                FROM posts p
                LEFT JOIN post_topics pt
                  ON p.source = pt.post_source
                 AND p.source_post_id = pt.post_source_id
                 AND pt.role = 'primary'
                ORDER BY p.saved_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [dict(row) for row in rows]

    def topics_overview(self) -> dict[str, list[dict[str, object]]]:
        with self._db.connection() as conn:
            stable = conn.execute(
                """
                SELECT t.slug, t.name, t.taxonomy_version, COUNT(pt.post_source) AS post_count
                FROM topics t
                LEFT JOIN post_topics pt
                  ON t.slug = pt.topic_slug AND pt.role = 'primary'
                GROUP BY t.slug, t.name, t.taxonomy_version
                ORDER BY post_count DESC, t.name ASC
                """
            ).fetchall()

            candidates = conn.execute(
                """
                SELECT id, label, keywords_json, evidence_count, confidence, state
                FROM topic_candidates
                ORDER BY updated_at DESC
                LIMIT 100
                """
            ).fetchall()

        return {
            "stable_topics": [dict(row) for row in stable],
            "candidates": [
                {
                    **dict(row),
                    "keywords": json.loads(row["keywords_json"] or "[]"),
                }
                for row in candidates
            ],
        }

    def search_posts(
        self,
        query: str,
        topic: str | None = None,
        status: str | None = None,
        source: str | None = None,
        min_confidence: float | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, object]]:
        if not query.strip():
            return []

        sql = """
            SELECT
              p.source,
              p.source_post_id,
                            p.url,
              p.title,
              p.content,
              p.saved_at,
              p.status,
              pt.topic_slug,
              pt.confidence
            FROM search_fts f
            JOIN posts p
              ON p.source = f.source AND p.source_post_id = f.source_post_id
            LEFT JOIN post_topics pt
              ON p.source = pt.post_source
             AND p.source_post_id = pt.post_source_id
             AND pt.role = 'primary'
            WHERE search_fts MATCH ?
        """
        params: list[object] = [query]

        if topic:
            sql += " AND pt.topic_slug = ?"
            params.append(topic)
        if status:
            sql += " AND p.status = ?"
            params.append(status)
        if source:
            sql += " AND p.source = ?"
            params.append(source)
        if min_confidence is not None:
            sql += " AND COALESCE(pt.confidence, 0) >= ?"
            params.append(min_confidence)
        if date_from:
            if len(date_from) == 10:
                sql += " AND substr(COALESCE(p.saved_at, ''), 1, 10) >= ?"
                params.append(date_from)
            else:
                sql += " AND COALESCE(p.saved_at, '') >= ?"
                params.append(date_from)
        if date_to:
            if len(date_to) == 10:
                sql += " AND substr(COALESCE(p.saved_at, ''), 1, 10) <= ?"
                params.append(date_to)
            else:
                sql += " AND COALESCE(p.saved_at, '') <= ?"
                params.append(date_to)

        sql += " ORDER BY p.saved_at DESC LIMIT ?"
        params.append(limit)

        with self._db.connection() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
        return [dict(row) for row in rows]

    def review_low_confidence(self, threshold: float = 0.5) -> list[dict[str, object]]:
        with self._db.connection() as conn:
            rows = conn.execute(
                """
                SELECT
                  p.source,
                  p.source_post_id,
                                    p.url,
                  p.title,
                  p.content,
                  pt.topic_slug,
                  pt.confidence,
                  pt.review_state
                FROM posts p
                JOIN post_topics pt
                  ON p.source = pt.post_source
                 AND p.source_post_id = pt.post_source_id
                WHERE pt.role = 'primary' AND (pt.confidence < ? OR pt.review_state IN ('pending', 'edited'))
                ORDER BY pt.confidence ASC
                """,
                (threshold,),
            ).fetchall()
        return [dict(row) for row in rows]

    def review_unmatched(self) -> list[dict[str, object]]:
        with self._db.connection() as conn:
            rows = conn.execute(
                """
                                SELECT p.source, p.source_post_id, p.url, p.title, p.content, p.saved_at
                FROM posts p
                LEFT JOIN post_topics pt
                  ON p.source = pt.post_source
                 AND p.source_post_id = pt.post_source_id
                 AND pt.role = 'primary'
                WHERE pt.topic_slug IS NULL
                ORDER BY p.saved_at DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def review_candidates(self) -> list[dict[str, object]]:
        with self._db.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, label, keywords_json, evidence_count, confidence, state, merged_into_topic_slug
                FROM topic_candidates
                WHERE state = 'pending'
                ORDER BY updated_at DESC
                """
            ).fetchall()
        return [
            {
                **dict(row),
                "keywords": json.loads(row["keywords_json"] or "[]"),
            }
            for row in rows
        ]

    def apply_assignment_action(
        self,
        post_source: str,
        post_source_id: str,
        action: str,
        primary_topic_slug: str | None = None,
        secondary_topic_slugs: list[str] | None = None,
    ) -> None:
        secondary_topic_slugs = secondary_topic_slugs or []
        with self._db.connection() as conn:
            if action == "approve":
                conn.execute(
                    """
                    UPDATE post_topics
                    SET review_state = 'accepted', updated_at = ?
                    WHERE post_source = ? AND post_source_id = ? AND role = 'primary'
                    """,
                    (_now(), post_source, post_source_id),
                )
            elif action == "reassign" and primary_topic_slug:
                conn.execute(
                    """
                    UPDATE post_topics
                    SET review_state = 'rejected', updated_at = ?
                    WHERE post_source = ? AND post_source_id = ? AND role = 'primary'
                    """,
                    (_now(), post_source, post_source_id),
                )
                conn.execute(
                    """
                    INSERT INTO post_topics (
                      post_source, post_source_id, topic_slug, role, confidence,
                      assignment_source, review_state, updated_at
                    ) VALUES (?, ?, ?, 'primary', 1.0, 'manual_review', 'accepted', ?)
                    ON CONFLICT(post_source, post_source_id, topic_slug, role, assignment_source) DO UPDATE SET
                      confidence = excluded.confidence,
                      review_state = excluded.review_state,
                      updated_at = excluded.updated_at
                    """,
                    (post_source, post_source_id, primary_topic_slug, _now()),
                )
            elif action == "adjust_secondary":
                conn.execute(
                    """
                    DELETE FROM post_topics
                    WHERE post_source = ? AND post_source_id = ? AND role = 'secondary'
                    """,
                    (post_source, post_source_id),
                )
                for slug in secondary_topic_slugs:
                    conn.execute(
                        """
                        INSERT INTO post_topics (
                          post_source, post_source_id, topic_slug, role, confidence,
                          assignment_source, review_state, updated_at
                        ) VALUES (?, ?, ?, 'secondary', 1.0, 'manual_review', 'accepted', ?)
                        ON CONFLICT(post_source, post_source_id, topic_slug, role, assignment_source) DO UPDATE SET
                          review_state = excluded.review_state,
                          updated_at = excluded.updated_at
                        """,
                        (post_source, post_source_id, slug, _now()),
                    )
            conn.commit()

    def decide_candidate(
        self,
        candidate_id: str,
        decision: str,
        target_topic_slug: str | None = None,
    ) -> None:
        state = {
            "promote": "promoted",
            "merge": "merged",
            "reject": "rejected",
        }.get(decision, decision)

        with self._db.connection() as conn:
            conn.execute(
                """
                UPDATE topic_candidates
                SET state = ?, merged_into_topic_slug = ?, updated_at = ?
                WHERE id = ?
                """,
                (state, target_topic_slug, _now(), candidate_id),
            )
            conn.commit()

    def trigger_manual_reprocess(self) -> str:
        run_id = str(uuid4())
        with self._db.connection() as conn:
            conn.execute(
                """
                INSERT INTO topic_runs (
                  id, run_type, taxonomy_version, embedding_model, representation_config,
                  input_count, output_count, error_count, started_at, finished_at,
                  status, diagnostics_json, updated_at
                ) VALUES (?, 'assignment', 'manual', 'n/a', ?, 0, 0, 0, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    json.dumps({"trigger": "ui_manual_reprocess"}),
                    _now(),
                    _now(),
                    "queued_manual_reprocess",
                    json.dumps({"source": "streamlit_ui"}),
                    _now(),
                ),
            )
            conn.commit()
        return run_id

    def settings_summary(self) -> dict[str, object]:
        with self._db.connection() as conn:
            taxonomy = conn.execute(
                "SELECT taxonomy_version, COUNT(*) AS count FROM topics GROUP BY taxonomy_version ORDER BY taxonomy_version DESC"
            ).fetchall()
            latest_batch = conn.execute(
                "SELECT batch_id, sent_at, source, processed, errors FROM ingest_batches ORDER BY finished_at DESC LIMIT 1"
            ).fetchone()
            runs = conn.execute(
                "SELECT run_type, status, started_at, finished_at FROM topic_runs ORDER BY updated_at DESC LIMIT 5"
            ).fetchall()

        return {
            "taxonomy_versions": [dict(row) for row in taxonomy],
            "latest_sync": dict(latest_batch) if latest_batch else None,
            "recent_topic_runs": [dict(row) for row in runs],
            "thresholds": {
                "stable_min_confidence": 0.5,
                "discovery_low_confidence": 0.45,
            },
        }

    def list_topics(self) -> list[str]:
        with self._db.connection() as conn:
            rows = conn.execute("SELECT DISTINCT slug FROM topics ORDER BY slug ASC").fetchall()
        return [row[0] for row in rows]

    def list_post_notes(self, post_source: str, post_source_id: str) -> list[dict[str, object]]:
        with self._db.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, body, updated_at
                FROM notes
                WHERE post_source = ? AND post_source_id = ?
                ORDER BY updated_at DESC
                """,
                (post_source, post_source_id),
            ).fetchall()
        return [dict(row) for row in rows]

    def upsert_note(
        self,
        post_source: str,
        post_source_id: str,
        body: str,
        note_id: str | None = None,
    ) -> str:
        resolved_id = note_id or str(uuid4())
        with self._db.connection() as conn:
            conn.execute(
                """
                INSERT INTO notes (id, post_source, post_source_id, body, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  body = excluded.body,
                  updated_at = excluded.updated_at
                """,
                (resolved_id, post_source, post_source_id, body, _now()),
            )
            conn.commit()
        return resolved_id
