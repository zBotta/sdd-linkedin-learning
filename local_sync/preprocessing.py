from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from typing import Any, Iterable, Mapping

from shared.schemas import NormalizedPost


_WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return _WHITESPACE_RE.sub(" ", value).strip()


def parse_datetime(value: Any, fallback: datetime | None = None) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str) and value.strip():
        text = value.strip().replace("Z", "+00:00")
        return datetime.fromisoformat(text)
    return fallback or datetime.now(UTC)


def build_content_hash(content: str, title: str | None = None) -> str:
    normalized_content = normalize_text(content)
    normalized_title = normalize_text(title)
    material = f"{normalized_title}\n{normalized_content}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def make_source_key(source: str, source_post_id: str) -> str:
    return f"{source}:{source_post_id}"


def normalize_post(raw: Mapping[str, Any], default_source: str = "linkedin_saved") -> NormalizedPost:
    source = str(raw.get("source") or default_source)
    source_post_id = str(raw.get("source_post_id") or raw.get("id") or "").strip()
    if not source_post_id:
        raise ValueError("source_post_id is required for normalization")

    title = normalize_text(raw.get("title")) or None
    content = normalize_text(raw.get("content") or raw.get("text"))
    if not content:
        raise ValueError(f"content is required for post {source_post_id}")

    metadata = raw.get("metadata_json") or raw.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {"raw_metadata": metadata}

    saved_at = parse_datetime(raw.get("saved_at"))
    published_at = parse_datetime(raw.get("published_at"), fallback=None) if raw.get("published_at") else None

    return NormalizedPost(
        source=source,
        source_post_id=source_post_id,
        url=raw.get("url"),
        author=normalize_text(raw.get("author")) or None,
        published_at=published_at,
        saved_at=saved_at,
        title=title,
        content=content,
        content_hash=build_content_hash(content=content, title=title),
        language=raw.get("language"),
        metadata_json=metadata,
    )


def deduplicate_posts(posts: Iterable[NormalizedPost]) -> list[NormalizedPost]:
    by_source_key: dict[str, NormalizedPost] = {}
    by_hash: dict[str, NormalizedPost] = {}

    for post in posts:
        current = by_source_key.get(post.source_key)
        if current is None or post.saved_at >= current.saved_at:
            by_source_key[post.source_key] = post

    for post in by_source_key.values():
        current = by_hash.get(post.content_hash)
        if current is None or post.saved_at >= current.saved_at:
            by_hash[post.content_hash] = post

    return sorted(by_hash.values(), key=lambda item: item.saved_at)
