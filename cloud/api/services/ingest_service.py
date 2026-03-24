from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from cloud.api.schemas import (
    IngestBatchRequest,
    IngestBatchResponse,
    TopicCandidateDecision,
    TopicCandidateResponse,
    TopicRunCreate,
)
from shared.db import Database


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class IngestService:
    def __init__(self, db: Database) -> None:
        self._db = db

    def health(self) -> dict[str, str]:
        with self._db.connection() as conn:
            conn.execute("SELECT 1")
        return {"status": "ok", "db": "ok", "timestamp": _now()}

    def sync_status(self) -> dict[str, object]:
        with self._db.connection() as conn:
            row = conn.execute(
                """
                SELECT batch_id, started_at, finished_at, processed, errors
                FROM ingest_batches
                ORDER BY finished_at DESC
                LIMIT 1
                """
            ).fetchone()
        if row is None:
            return {
                "lastRunId": None,
                "status": "never_run",
                "startedAt": None,
                "finishedAt": None,
                "processed": 0,
                "errors": 0,
            }
        return {
            "lastRunId": row["batch_id"],
            "status": "success" if row["errors"] == 0 else "failed",
            "startedAt": row["started_at"],
            "finishedAt": row["finished_at"],
            "processed": row["processed"],
            "errors": row["errors"],
        }

    def ingest_batch(self, payload: IngestBatchRequest) -> IngestBatchResponse:
        started_at = _now()
        with self._db.connection() as conn:
            existing = conn.execute(
                "SELECT batch_id FROM ingest_batches WHERE batch_id = ?",
                (payload.batch_id,),
            ).fetchone()
            if existing is not None:
                return IngestBatchResponse(
                    batchId=payload.batch_id,
                    applied=False,
                    upsertCounts={
                        "posts": 0,
                        "topics": 0,
                        "postTopics": 0,
                        "topicCandidates": 0,
                        "notes": 0,
                    },
                    warnings=["duplicate_batch_ignored"],
                )

            counts = {"posts": 0, "topics": 0, "postTopics": 0, "topicCandidates": 0, "notes": 0}

            for post in payload.posts:
                conn.execute(
                    """
                    INSERT INTO posts (
                      source, source_post_id, url, author, published_at, saved_at,
                      title, content, content_hash, language, metadata_json,
                      summary, importance_score, novelty_score, status, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(source, source_post_id) DO UPDATE SET
                      url=excluded.url,
                      author=excluded.author,
                      published_at=excluded.published_at,
                      saved_at=excluded.saved_at,
                      title=excluded.title,
                      content=excluded.content,
                      content_hash=excluded.content_hash,
                      language=excluded.language,
                      metadata_json=excluded.metadata_json,
                      summary=excluded.summary,
                      importance_score=excluded.importance_score,
                      novelty_score=excluded.novelty_score,
                      status=excluded.status,
                      updated_at=excluded.updated_at
                    """,
                    (
                        post.source,
                        post.source_post_id,
                        post.url,
                        post.author,
                        post.published_at.isoformat() if post.published_at else None,
                        post.saved_at.isoformat() if post.saved_at else None,
                        post.title,
                        post.content,
                        post.content_hash,
                        post.language,
                        json.dumps(post.metadata_json),
                        post.summary,
                        post.importance_score,
                        post.novelty_score,
                        post.status,
                        _now(),
                    ),
                )
                counts["posts"] += 1

            for topic in payload.topics:
                conn.execute(
                    """
                    INSERT INTO topics (slug, taxonomy_version, name, description, source_type, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(slug, taxonomy_version) DO UPDATE SET
                      name=excluded.name,
                      description=excluded.description,
                      source_type=excluded.source_type,
                      updated_at=excluded.updated_at
                    """,
                    (
                        topic.slug,
                        topic.taxonomy_version,
                        topic.name,
                        topic.description,
                        topic.source_type,
                        _now(),
                    ),
                )
                counts["topics"] += 1

            for rel in payload.post_topics:
                conn.execute(
                    """
                    INSERT INTO post_topics (
                      post_source, post_source_id, topic_slug, role, confidence,
                      assignment_source, review_state, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(post_source, post_source_id, topic_slug, role, assignment_source) DO UPDATE SET
                      confidence=excluded.confidence,
                      review_state=excluded.review_state,
                      updated_at=excluded.updated_at
                    """,
                    (
                        rel.post_source,
                        rel.post_source_id,
                        rel.topic_slug,
                        rel.role,
                        rel.confidence,
                        rel.assignment_source or "taxonomy_assignment",
                        rel.review_state,
                        _now(),
                    ),
                )
                counts["postTopics"] += 1

            for cand in payload.topic_candidates:
                conn.execute(
                    """
                    INSERT INTO topic_candidates (
                      id, label, keywords_json, evidence_count, confidence, state,
                      merged_into_topic_slug, run_id, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                      label=excluded.label,
                      keywords_json=excluded.keywords_json,
                      evidence_count=excluded.evidence_count,
                      confidence=excluded.confidence,
                      state=excluded.state,
                      merged_into_topic_slug=excluded.merged_into_topic_slug,
                      run_id=excluded.run_id,
                      updated_at=excluded.updated_at
                    """,
                    (
                        cand.id,
                        cand.label,
                        json.dumps(cand.keywords),
                        cand.evidence_count,
                        cand.confidence,
                        cand.state,
                        cand.merged_into_topic_slug,
                        payload.batch_id,
                        _now(),
                    ),
                )
                counts["topicCandidates"] += 1

            for note in payload.notes:
                note_id = note.id or str(uuid4())
                conn.execute(
                    """
                    INSERT INTO notes (id, post_source, post_source_id, body, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                      body=excluded.body,
                      updated_at=excluded.updated_at
                    """,
                    (
                        note_id,
                        note.post_source,
                        note.post_source_id,
                        note.body,
                        _now(),
                    ),
                )
                counts["notes"] += 1

            self._refresh_search(conn)

            conn.execute(
                """
                INSERT INTO ingest_batches (
                  batch_id, sent_at, source, applied, processed, errors, started_at, finished_at
                ) VALUES (?, ?, ?, 1, ?, 0, ?, ?)
                """,
                (
                    payload.batch_id,
                    payload.sent_at.isoformat(),
                    payload.source,
                    counts["posts"],
                    started_at,
                    _now(),
                ),
            )
            conn.commit()

        return IngestBatchResponse(batchId=payload.batch_id, applied=True, upsertCounts=counts, warnings=[])

    def create_topic_run(self, payload: TopicRunCreate) -> dict[str, object]:
        run_id = str(uuid4())
        with self._db.connection() as conn:
            conn.execute(
                """
                INSERT INTO topic_runs (
                  id, run_type, taxonomy_version, embedding_model, representation_config,
                  input_count, output_count, error_count, started_at, finished_at,
                  status, diagnostics_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    payload.run_type,
                    payload.taxonomy_version,
                    payload.embedding_model,
                    json.dumps(payload.representation_config) if payload.representation_config else None,
                    payload.input_count,
                    payload.output_count,
                    payload.error_count,
                    payload.started_at.isoformat(),
                    payload.finished_at.isoformat() if payload.finished_at else None,
                    payload.status,
                    json.dumps(payload.diagnostics_json) if payload.diagnostics_json else None,
                    _now(),
                ),
            )
            conn.commit()

        response = payload.model_dump(by_alias=True)
        response["id"] = run_id
        return response

    def list_topic_candidates(self, state: str | None = None) -> list[TopicCandidateResponse]:
        sql = """
            SELECT id, label, keywords_json, evidence_count, confidence, state, merged_into_topic_slug
            FROM topic_candidates
        """
        params: tuple[object, ...] = ()
        if state:
            sql += " WHERE state = ?"
            params = (state,)
        sql += " ORDER BY updated_at DESC"

        with self._db.connection() as conn:
            rows = conn.execute(sql, params).fetchall()

        results: list[TopicCandidateResponse] = []
        for row in rows:
            results.append(
                TopicCandidateResponse(
                    id=row["id"],
                    label=row["label"],
                    keywords=json.loads(row["keywords_json"] or "[]"),
                    evidenceCount=row["evidence_count"],
                    confidence=row["confidence"],
                    state=row["state"],
                    mergedIntoTopicSlug=row["merged_into_topic_slug"],
                )
            )
        return results

    def apply_candidate_decision(self, candidate_id: str, payload: TopicCandidateDecision) -> TopicCandidateResponse | None:
        mapped_state = {
            "promote": "promoted",
            "merge": "merged",
            "reject": "rejected",
        }.get(payload.decision)
        if mapped_state is None:
            mapped_state = payload.decision

        with self._db.connection() as conn:
            current = conn.execute(
                """
                SELECT id, label, keywords_json, evidence_count, confidence, state, merged_into_topic_slug
                FROM topic_candidates
                WHERE id = ?
                """,
                (candidate_id,),
            ).fetchone()
            if current is None:
                return None

            conn.execute(
                """
                UPDATE topic_candidates
                SET state = ?, merged_into_topic_slug = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    mapped_state,
                    payload.target_topic_slug,
                    _now(),
                    candidate_id,
                ),
            )
            conn.commit()

            row = conn.execute(
                """
                SELECT id, label, keywords_json, evidence_count, confidence, state, merged_into_topic_slug
                FROM topic_candidates
                WHERE id = ?
                """,
                (candidate_id,),
            ).fetchone()

        return TopicCandidateResponse(
            id=row["id"],
            label=row["label"],
            keywords=json.loads(row["keywords_json"] or "[]"),
            evidenceCount=row["evidence_count"],
            confidence=row["confidence"],
            state=row["state"],
            mergedIntoTopicSlug=row["merged_into_topic_slug"],
        )

    @staticmethod
    def _refresh_search(conn) -> None:
        conn.execute("DELETE FROM search_fts")
        conn.execute(
            """
            INSERT INTO search_fts (source, source_post_id, title, content, summary, notes)
            SELECT
              p.source,
              p.source_post_id,
              COALESCE(p.title, ''),
              COALESCE(p.content, ''),
              COALESCE(p.summary, ''),
              COALESCE(GROUP_CONCAT(n.body, ' '), '')
            FROM posts p
            LEFT JOIN notes n
              ON p.source = n.post_source AND p.source_post_id = n.post_source_id
            GROUP BY p.source, p.source_post_id
            """
        )
