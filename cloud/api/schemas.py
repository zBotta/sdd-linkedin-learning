from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PostDelta(BaseModel):
    source: str
    source_post_id: str = Field(alias="sourcePostId")
    url: str | None = None
    author: str | None = None
    published_at: datetime | None = Field(default=None, alias="publishedAt")
    saved_at: datetime | None = Field(default=None, alias="savedAt")
    title: str | None = None
    content: str
    content_hash: str = Field(alias="contentHash")
    language: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict, alias="metadataJson")
    summary: str | None = None
    importance_score: float | None = Field(default=None, alias="importanceScore")
    novelty_score: float | None = Field(default=None, alias="noveltyScore")
    status: str | None = None


class TopicDelta(BaseModel):
    slug: str
    name: str
    description: str | None = None
    taxonomy_version: str = Field(alias="taxonomyVersion")
    source_type: str | None = Field(default=None, alias="sourceType")


class PostTopicDelta(BaseModel):
    post_source: str = Field(alias="postSource")
    post_source_id: str = Field(alias="postSourceId")
    topic_slug: str = Field(alias="topicSlug")
    role: str
    confidence: float
    assignment_source: str | None = Field(default=None, alias="assignmentSource")
    review_state: str | None = Field(default=None, alias="reviewState")


class NoteDelta(BaseModel):
    id: str | None = None
    post_source: str = Field(alias="postSource")
    post_source_id: str = Field(alias="postSourceId")
    body: str


class TopicCandidateDelta(BaseModel):
    id: str
    label: str
    keywords: list[str] = Field(default_factory=list)
    evidence_count: int = Field(alias="evidenceCount")
    confidence: float | None = None
    state: str
    merged_into_topic_slug: str | None = Field(default=None, alias="mergedIntoTopicSlug")


class IngestBatchRequest(BaseModel):
    batch_id: str = Field(alias="batchId")
    sent_at: datetime = Field(alias="sentAt")
    source: str = "local_sync"
    posts: list[PostDelta]
    topics: list[TopicDelta] = Field(default_factory=list)
    post_topics: list[PostTopicDelta] = Field(default_factory=list, alias="postTopics")
    topic_candidates: list[TopicCandidateDelta] = Field(default_factory=list, alias="topicCandidates")
    notes: list[NoteDelta] = Field(default_factory=list)


class IngestBatchResponse(BaseModel):
    batch_id: str = Field(alias="batchId")
    applied: bool
    upsert_counts: dict[str, int] = Field(alias="upsertCounts")
    warnings: list[str] = Field(default_factory=list)


class TopicRunCreate(BaseModel):
    run_type: str = Field(alias="runType")
    taxonomy_version: str = Field(alias="taxonomyVersion")
    embedding_model: str = Field(alias="embeddingModel")
    representation_config: dict[str, Any] | None = Field(default=None, alias="representationConfig")
    input_count: int | None = Field(default=None, alias="inputCount")
    output_count: int | None = Field(default=None, alias="outputCount")
    error_count: int | None = Field(default=None, alias="errorCount")
    started_at: datetime = Field(alias="startedAt")
    finished_at: datetime | None = Field(default=None, alias="finishedAt")
    status: str
    diagnostics_json: dict[str, Any] | None = Field(default=None, alias="diagnosticsJson")


class TopicCandidateDecision(BaseModel):
    decision: str
    target_topic_slug: str | None = Field(default=None, alias="targetTopicSlug")
    note: str | None = None


class HealthResponse(BaseModel):
    status: str
    db: str
    timestamp: datetime


class SyncStatusResponse(BaseModel):
    last_run_id: str | None = Field(default=None, alias="lastRunId")
    status: str | None = None
    started_at: datetime | None = Field(default=None, alias="startedAt")
    finished_at: datetime | None = Field(default=None, alias="finishedAt")
    processed: int = 0
    errors: int = 0


class TopicCandidateResponse(BaseModel):
    id: str
    label: str
    keywords: list[str]
    evidence_count: int = Field(alias="evidenceCount")
    confidence: float | None = None
    state: str
    merged_into_topic_slug: str | None = Field(default=None, alias="mergedIntoTopicSlug")
