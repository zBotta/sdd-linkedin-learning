from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class TopicDefinition(BaseModel):
    slug: str
    name: str
    keywords: list[str] = Field(default_factory=list)


class TaxonomyConfig(BaseModel):
    taxonomy_version: str
    zeroshot_min_similarity: float = 0.35
    secondary_min_similarity: float = 0.5
    topics: list[TopicDefinition]


def load_taxonomy(path: Path) -> TaxonomyConfig:
    if not path.exists():
        raise FileNotFoundError(f"Taxonomy file not found: {path}")

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Invalid taxonomy file: expected object root")

    return TaxonomyConfig.model_validate(data)


def validate_taxonomy(config: TaxonomyConfig) -> None:
    if not config.topics:
        raise ValueError("at least one topic is required")

    seen: set[str] = set()
    for topic in config.topics:
        if topic.slug in seen:
            raise ValueError(f"Duplicate topic slug: {topic.slug}")
        seen.add(topic.slug)

    if config.secondary_min_similarity < config.zeroshot_min_similarity:
        raise ValueError("secondary_min_similarity must be >= zeroshot_min_similarity")
