from __future__ import annotations

import json
from datetime import datetime, timezone
import time
from typing import Any
from uuid import uuid4
from urllib import error, request

from shared.schemas import NormalizedPost, PushResult


class PushClient:
    """Authenticated push client with a safe dry-run mode for local prototyping."""

    def __init__(
        self,
        base_url: str,
        token: str,
        enabled: bool,
        timeout_seconds: int = 20,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._enabled = enabled
        self._timeout_seconds = timeout_seconds

    def build_payload(
        self,
        posts: list[NormalizedPost],
        topics: list[dict[str, Any]] | None = None,
        post_topics: list[dict[str, Any]] | None = None,
        topic_candidates: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        _ = metadata

        payload_posts = [
            {
                "source": item.source,
                "sourcePostId": item.source_post_id,
                "url": item.url,
                "author": item.author,
                "publishedAt": item.published_at.isoformat() if item.published_at else None,
                "savedAt": item.saved_at.isoformat() if item.saved_at else None,
                "title": item.title,
                "content": item.content,
                "contentHash": item.content_hash,
                "language": item.language,
                "metadataJson": item.metadata_json,
            }
            for item in posts
        ]

        payload_topics: list[dict[str, Any]] = []
        for row in topics or []:
            if all(key in row for key in ("slug", "name", "taxonomyVersion")):
                payload_topics.append(
                    {
                        "slug": row["slug"],
                        "name": row["name"],
                        "description": row.get("description"),
                        "taxonomyVersion": row["taxonomyVersion"],
                        "sourceType": row.get("sourceType"),
                    }
                )

        payload_post_topics: list[dict[str, Any]] = []
        for row in post_topics or []:
            if all(key in row for key in ("postSource", "postSourceId", "topicSlug", "role", "confidence")):
                payload_post_topics.append(
                    {
                        "postSource": row["postSource"],
                        "postSourceId": row["postSourceId"],
                        "topicSlug": row["topicSlug"],
                        "role": row["role"],
                        "confidence": row["confidence"],
                        "assignmentSource": row.get("assignmentSource"),
                        "reviewState": row.get("reviewState"),
                    }
                )

        payload_topic_candidates: list[dict[str, Any]] = []
        for row in topic_candidates or []:
            candidate_id = row.get("id") or row.get("candidate_id")
            if not candidate_id:
                continue
            keywords = row.get("keywords") or []
            evidence_count = row.get("evidenceCount")
            if evidence_count is None:
                evidence_count = len(row.get("evidence_source_keys") or [])
            payload_topic_candidates.append(
                {
                    "id": candidate_id,
                    "label": row.get("label", ""),
                    "keywords": keywords,
                    "evidenceCount": int(evidence_count),
                    "confidence": row.get("confidence"),
                    "state": row.get("state", "pending"),
                    "mergedIntoTopicSlug": row.get("mergedIntoTopicSlug") or row.get("merged_into_topic_slug"),
                }
            )

        return {
            "batchId": str(uuid4()),
            "sentAt": datetime.now(timezone.utc).isoformat(),
            "source": "local_sync",
            "posts": payload_posts,
            "topics": payload_topics,
            "postTopics": payload_post_topics,
            "topicCandidates": payload_topic_candidates,
            "notes": [],
        }

    def push_payload(self, payload: dict[str, Any]) -> PushResult:
        return self._post_json("/ingest/batch", payload, success_label="Payload sent")

    def create_topic_run(self, payload: dict[str, Any]) -> PushResult:
        return self._post_json("/topic-runs", payload, success_label="Topic run registered")

    def _post_json(self, path: str, payload: dict[str, Any], *, success_label: str) -> PushResult:
        if not self._enabled:
            return PushResult(applied=True, dry_run=True, message=f"{success_label} skipped (push disabled)")

        if not self._base_url or not self._token:
            return PushResult(
                applied=False,
                dry_run=False,
                status_code=None,
                message="Missing CLOUD_API_BASE_URL or CLOUD_INGEST_TOKEN",
            )

        endpoint = f"{self._base_url}{path}"
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._token}",
        }

        max_attempts = 3
        delay_seconds = 1.0
        last_result: PushResult | None = None

        for attempt in range(1, max_attempts + 1):
            req = request.Request(endpoint, data=body, headers=headers, method="POST")
            try:
                with request.urlopen(req, timeout=self._timeout_seconds) as response:
                    return PushResult(
                        applied=200 <= response.status < 300,
                        dry_run=False,
                        status_code=response.status,
                        message=f"{success_label} (attempt {attempt}/{max_attempts})",
                    )
            except error.HTTPError as exc:
                last_result = PushResult(
                    applied=False,
                    dry_run=False,
                    status_code=exc.code,
                    message=f"HTTPError attempt {attempt}/{max_attempts}: {exc}",
                )
                retryable = 500 <= exc.code < 600 or exc.code == 429
                if not retryable or attempt == max_attempts:
                    return last_result
            except error.URLError as exc:
                last_result = PushResult(
                    applied=False,
                    dry_run=False,
                    status_code=None,
                    message=f"URLError attempt {attempt}/{max_attempts}: {exc}",
                )
                if attempt == max_attempts:
                    return last_result

            time.sleep(delay_seconds)
            delay_seconds *= 2

        return last_result or PushResult(
            applied=False,
            dry_run=False,
            status_code=None,
            message="Push failed after retries",
        )
