from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class TopicMatch(BaseModel):
    topic_slug: str
    topic_name: str
    confidence: float
    role: str


class PostClassification(BaseModel):
    source_key: str
    taxonomy_version: str
    matches: list[TopicMatch] = Field(default_factory=list)


class ClassificationRunMetadata(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    status: str = "running"
    taxonomy_version: str
    backend: str
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    zeroshot_min_similarity: float
    secondary_min_similarity: float
    processed_count: int = 0
    matched_count: int = 0
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class DiscoveryCandidate(BaseModel):
    candidate_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    taxonomy_version: str
    label: str
    keywords: list[str] = Field(default_factory=list)
    evidence_source_keys: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    state: str = "pending"


class DiscoveryRunMetadata(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    status: str = "running"
    taxonomy_version: str
    backend: str
    input_count: int = 0
    candidate_count: int = 0
    diagnostics: dict[str, Any] = Field(default_factory=dict)


def append_run_metadata(path: Path, metadata: ClassificationRunMetadata) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(metadata.model_dump(mode="json")) + "\n")


def append_discovery_run_metadata(path: Path, metadata: DiscoveryRunMetadata) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(metadata.model_dump(mode="json")) + "\n")


def append_discovery_candidates(path: Path, candidates: list[DiscoveryCandidate]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for item in candidates:
            handle.write(json.dumps(item.model_dump(mode="json")) + "\n")
