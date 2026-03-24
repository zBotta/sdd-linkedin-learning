from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from shared.models import ClassificationRunMetadata, PostClassification, append_run_metadata
from shared.schemas import NormalizedPost, PushResult
from shared.taxonomy import TaxonomyConfig, load_taxonomy, validate_taxonomy

from .config import LocalSyncConfig
from .linkedin_scraper import LinkedInSavedScraper
from .preprocessing import deduplicate_posts, normalize_post
from .push_client import PushClient
from .state_store import StateStore
from .taxonomy_assignment import TaxonomyAssigner


class ScraperProtocol(Protocol):
    def fetch_saved_posts(self, limit: int = 100) -> list[dict]: ...


class PushClientProtocol(Protocol):
    def build_payload(self, posts: list[NormalizedPost]) -> dict: ...

    def push_payload(self, payload: dict) -> PushResult: ...


class TaxonomyAssignerProtocol(Protocol):
    def assign(
        self,
        posts: list[NormalizedPost],
        taxonomy: TaxonomyConfig,
    ) -> tuple[list[PostClassification], ClassificationRunMetadata]: ...


class SyncAgent:
    """Run one local sync cycle: scrape -> normalize -> dedup -> export -> optional push."""

    def __init__(
        self,
        config: LocalSyncConfig,
        scraper: ScraperProtocol | None = None,
        state_store: StateStore | None = None,
        push_client: PushClientProtocol | None = None,
        taxonomy_assigner: TaxonomyAssignerProtocol | None = None,
    ) -> None:
        self._config = config
        self._scraper = scraper or LinkedInSavedScraper(config)
        self._state_store = state_store or StateStore(config.state_path)
        self._push_client = push_client or PushClient(
            base_url=config.cloud_api_base_url,
            token=config.cloud_ingest_token,
            enabled=config.push_enabled,
            timeout_seconds=config.push_timeout_seconds,
        )
        self._taxonomy_assigner = taxonomy_assigner or TaxonomyAssigner(
            min_similarity=config.zeroshot_min_similarity,
            secondary_min_similarity=config.secondary_min_similarity,
        )

    def run_once(self, limit: int = 100) -> dict[str, object]:
        raw_posts = self._scraper.fetch_saved_posts(limit=limit)

        normalized = [normalize_post(item) for item in raw_posts]
        deduped = deduplicate_posts(normalized)
        new_posts = self._state_store.filter_new(deduped)

        taxonomy = load_taxonomy(self._config.taxonomy_path)
        validate_taxonomy(taxonomy)
        classifications, run_metadata = self._taxonomy_assigner.assign(new_posts, taxonomy)

        batch_id = str(uuid4())
        exported_path = self._export_normalized_posts(
            new_posts,
            classifications,
            run_metadata,
            batch_id=batch_id,
        )

        payload = self._push_client.build_payload(new_posts)
        push_result = self._push_client.push_payload(payload)

        self._state_store.mark_synced(new_posts, batch_id=batch_id)
        append_run_metadata(self._config.classification_runs_path, run_metadata)

        return {
            "batch_id": batch_id,
            "scraped_count": len(raw_posts),
            "normalized_count": len(normalized),
            "deduped_count": len(deduped),
            "new_count": len(new_posts),
            "classification_run_id": run_metadata.run_id,
            "classification_matched_count": run_metadata.matched_count,
            "export_path": str(exported_path) if exported_path else None,
            "push_result": push_result.model_dump(),
        }

    def _export_normalized_posts(
        self,
        posts: list[NormalizedPost],
        classifications: list[PostClassification],
        run_metadata: ClassificationRunMetadata,
        batch_id: str,
    ) -> Path | None:
        if not self._config.export_enabled:
            return None

        self._config.export_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        path = self._config.export_dir / f"batch_{timestamp}_{batch_id}.json"

        payload = {
            "batchId": batch_id,
            "exportedAt": datetime.now(UTC).isoformat(),
            "posts": [post.model_dump(mode="json") for post in posts],
            "classifications": [item.model_dump(mode="json") for item in classifications],
            "classificationRun": run_metadata.model_dump(mode="json"),
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path
