from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from shared.models import (
    ClassificationRunMetadata,
    DiscoveryCandidate,
    DiscoveryRunMetadata,
    PostClassification,
    append_run_metadata,
)
from shared.schemas import NormalizedPost, PushResult
from shared.taxonomy import TaxonomyConfig, load_taxonomy, validate_taxonomy

from .config import LocalSyncConfig
from .linkedin_scraper import LinkedInSavedScraper
from .observability import build_confidence_bands
from .preprocessing import deduplicate_posts, normalize_post
from .push_client import PushClient
from .state_store import StateStore
from .taxonomy_assignment import TaxonomyAssigner
from .topic_discovery import TopicDiscoveryPipeline


class ScraperProtocol(Protocol):
    def fetch_saved_posts(
        self,
        limit: int = 100,
        *,
        seen_source_keys: set[str] | None = None,
        stop_on_first_seen: bool = True,
    ) -> list[dict]: ...


class PushClientProtocol(Protocol):
    def build_payload(
        self,
        posts: list[NormalizedPost],
        post_topics: list[dict] | None = None,
        topic_candidates: list[dict] | None = None,
        metadata: dict | None = None,
    ) -> dict: ...

    def push_payload(self, payload: dict) -> PushResult: ...


class TaxonomyAssignerProtocol(Protocol):
    def assign(
        self,
        posts: list[NormalizedPost],
        taxonomy: TaxonomyConfig,
    ) -> tuple[list[PostClassification], ClassificationRunMetadata]: ...


class TopicDiscoveryProtocol(Protocol):
    def discover(
        self,
        posts: list[NormalizedPost],
        classifications: list[PostClassification],
        taxonomy_version: str,
    ) -> tuple[list[DiscoveryCandidate], DiscoveryRunMetadata]: ...

    def persist(
        self,
        candidates: list[DiscoveryCandidate],
        run: DiscoveryRunMetadata,
        run_path,
        candidates_path,
    ) -> None: ...


class SyncAgent:
    """Run one local sync cycle: scrape -> normalize -> dedup -> export -> optional push."""

    def __init__(
        self,
        config: LocalSyncConfig,
        scraper: ScraperProtocol | None = None,
        state_store: StateStore | None = None,
        push_client: PushClientProtocol | None = None,
        taxonomy_assigner: TaxonomyAssignerProtocol | None = None,
        topic_discovery: TopicDiscoveryProtocol | None = None,
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
        self._topic_discovery = topic_discovery or TopicDiscoveryPipeline(
            low_confidence_threshold=config.discovery_low_confidence_threshold,
            recent_window_days=config.discovery_recent_window_days,
            llama_cpp_model_path=str(config.llama_cpp_model_path) if config.llama_cpp_model_path else None,
            local_embedding_model_path=(
                str(config.local_embedding_model_path) if config.local_embedding_model_path else None
            ),
        )

    def run_once(self, limit: int = 100) -> dict[str, object]:
        full_rescrape = self._config.full_rescrape
        seen_source_keys = set() if full_rescrape else self._state_store.seen_source_keys
        stop_on_first_seen = self._config.linkedin_stop_on_first_seen and not full_rescrape

        try:
            raw_posts = self._scraper.fetch_saved_posts(
                limit=limit,
                seen_source_keys=seen_source_keys,
                stop_on_first_seen=stop_on_first_seen,
            )
        except TypeError:
            raw_posts = self._scraper.fetch_saved_posts(limit=limit)

        normalized = [normalize_post(item) for item in raw_posts]
        deduped = deduplicate_posts(normalized)
        new_posts = deduped if self._config.full_rescrape else self._state_store.filter_new(deduped)


        taxonomy = load_taxonomy(self._config.taxonomy_path)
        validate_taxonomy(taxonomy)
        classifications, run_metadata = self._taxonomy_assigner.assign(new_posts, taxonomy)

        candidates, discovery_run = self._topic_discovery.discover(
            new_posts,
            classifications,
            taxonomy_version=taxonomy.taxonomy_version,
        )
        self._topic_discovery.persist(
            candidates,
            discovery_run,
            self._config.discovery_runs_path,
            self._config.discovery_candidates_path,
        )

        discovery_post_topics = self._build_discovery_post_topics(candidates)
        discovery_telemetry = self._build_discovery_telemetry(candidates, discovery_run)

        batch_id = str(uuid4())
        exported_path = self._export_normalized_posts(
            new_posts,
            classifications,
            run_metadata,
            candidates,
            discovery_run,
            discovery_telemetry,
            discovery_post_topics,
            batch_id=batch_id,
        )

        try:
            payload = self._push_client.build_payload(
                new_posts,
                post_topics=discovery_post_topics,
                topic_candidates=[item.model_dump(mode="json") for item in candidates],
                metadata={
                    "classificationRunId": run_metadata.run_id,
                    "discoveryRunId": discovery_run.run_id,
                    "discoveryTelemetry": discovery_telemetry,
                },
            )
        except TypeError:
            payload = self._push_client.build_payload(new_posts)
        push_result = self._push_client.push_payload(payload)

        if push_result.applied:
            self._state_store.mark_synced(new_posts, batch_id=batch_id)
        append_run_metadata(self._config.classification_runs_path, run_metadata)

        return {
            "batch_id": batch_id,
            "full_rescrape": full_rescrape,
            "stop_on_first_seen": stop_on_first_seen,
            "scraped_count": len(raw_posts),
            "normalized_count": len(normalized),
            "deduped_count": len(deduped),
            "new_count": len(new_posts),
            "classification_run_id": run_metadata.run_id,
            "classification_matched_count": run_metadata.matched_count,
            "discovery_run_id": discovery_run.run_id,
            "discovery_candidate_count": len(candidates),
            "export_path": str(exported_path) if exported_path else None,
            "push_result": push_result.model_dump(),
        }

    def manual_reprocess_backlog(self, limit: int = 500) -> dict[str, object]:
        """Explicit user-triggered backlog reprocess path; never run automatically."""
        raw_posts = self._scraper.fetch_saved_posts(limit=limit)
        normalized = [normalize_post(item) for item in raw_posts]
        deduped = deduplicate_posts(normalized)

        taxonomy = load_taxonomy(self._config.taxonomy_path)
        validate_taxonomy(taxonomy)
        classifications, run_metadata = self._taxonomy_assigner.assign(deduped, taxonomy)

        candidates, discovery_run = self._topic_discovery.discover(
            deduped,
            classifications,
            taxonomy_version=taxonomy.taxonomy_version,
        )
        self._topic_discovery.persist(
            candidates,
            discovery_run,
            self._config.discovery_runs_path,
            self._config.discovery_candidates_path,
        )
        append_run_metadata(self._config.classification_runs_path, run_metadata)

        return {
            "mode": "manual_reprocess",
            "reprocessed_count": len(deduped),
            "classification_run_id": run_metadata.run_id,
            "discovery_run_id": discovery_run.run_id,
            "discovery_candidate_count": len(candidates),
        }

    def _export_normalized_posts(
        self,
        posts: list[NormalizedPost],
        classifications: list[PostClassification],
        run_metadata: ClassificationRunMetadata,
        candidates: list[DiscoveryCandidate],
        discovery_run: DiscoveryRunMetadata,
        discovery_telemetry: dict[str, object],
        discovery_post_topics: list[dict[str, object]],
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
            "topicCandidates": [item.model_dump(mode="json") for item in candidates],
            "discoveryRun": discovery_run.model_dump(mode="json"),
            "discoveryPostTopics": discovery_post_topics,
            "discoveryTelemetry": discovery_telemetry,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    @staticmethod
    def _build_discovery_post_topics(candidates: list[DiscoveryCandidate]) -> list[dict[str, object]]:
        post_topics: list[dict[str, object]] = []
        for candidate in candidates:
            for source_key in candidate.evidence_source_keys:
                post_topics.append(
                    {
                        "sourceKey": source_key,
                        "topicLabel": candidate.label,
                        "role": "discovery_candidate",
                        "confidence": candidate.confidence,
                        "candidateId": candidate.candidate_id,
                    }
                )
        return post_topics

    @staticmethod
    def _build_discovery_telemetry(
        candidates: list[DiscoveryCandidate],
        run: DiscoveryRunMetadata,
    ) -> dict[str, object]:
        confidences = [item.confidence for item in candidates]
        evidence_sizes = [len(item.evidence_source_keys) for item in candidates]
        backlog_age_days = int(run.diagnostics.get("backlog_age_days", 0))
        return {
            "candidate_count": len(candidates),
            "confidence_bands": build_confidence_bands(confidences),
            "average_evidence_size": (sum(evidence_sizes) / len(evidence_sizes)) if evidence_sizes else 0.0,
            "backlog_age_days": backlog_age_days,
            "scope_counts": run.diagnostics.get("scope_counts", {}),
        }
