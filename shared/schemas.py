from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class NormalizedPost(BaseModel):
    """Canonical normalized post payload produced by local sync."""

    model_config = ConfigDict(extra="ignore")

    source: str = "linkedin_saved"
    source_post_id: str
    url: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    saved_at: datetime
    title: str | None = None
    content: str
    content_hash: str
    language: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @property
    def source_key(self) -> str:
        return f"{self.source}:{self.source_post_id}"


class IngestBatchRequest(BaseModel):
    """Phase-1 payload scaffold for future cloud ingest endpoint."""

    batch_id: str = Field(default_factory=lambda: str(uuid4()))
    sent_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "local_sync"
    posts: list[NormalizedPost]
    post_topics: list[dict[str, Any]] = Field(default_factory=list)
    topic_candidates: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PushResult(BaseModel):
    """Result object for local push attempts."""

    applied: bool
    dry_run: bool
    status_code: int | None = None
    message: str = ""
