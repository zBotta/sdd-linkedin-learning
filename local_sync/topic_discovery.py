from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from importlib.util import find_spec
from pathlib import Path

from shared.models import (
    DiscoveryCandidate,
    DiscoveryRunMetadata,
    PostClassification,
    append_discovery_candidates,
    append_discovery_run_metadata,
)
from shared.schemas import NormalizedPost

from .topic_label_refinement import RefinementConfig, build_representation_model


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _bertopic_enabled() -> bool:
    return not _parse_bool(os.getenv("LOCAL_SYNC_DISABLE_BERTOPIC"), False)


def _build_embedding_model() -> object:
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    if not _parse_bool(os.getenv("LOCAL_SYNC_EMBEDDINGS_LOCAL_ONLY"), False):
        return model_name

    from sentence_transformers import SentenceTransformer

    # Force local cache usage and avoid network calls (useful behind restrictive TLS proxies).
    return SentenceTransformer(model_name, local_files_only=True)


class TopicDiscoveryPipeline:
    """Discover candidate topics from unmatched or low-confidence local posts."""

    def __init__(
        self,
        low_confidence_threshold: float = 0.45,
        recent_window_days: int = 7,
        llama_cpp_model_path: str | None = None,
        local_embedding_model_path: str | None = None,
    ) -> None:
        self._low_confidence_threshold = low_confidence_threshold
        self._recent_window_days = recent_window_days
        self._llama_cpp_model_path = llama_cpp_model_path
        self._local_embedding_model_path = local_embedding_model_path

    def select_scope(
        self,
        posts: list[NormalizedPost],
        classifications: list[PostClassification],
    ) -> dict[str, list[NormalizedPost]]:
        by_key = {item.source_key: item for item in classifications}
        now = datetime.now(UTC)
        recent_cutoff = now - timedelta(days=self._recent_window_days)

        unmatched: list[NormalizedPost] = []
        low_confidence: list[NormalizedPost] = []
        recent: list[NormalizedPost] = []

        for post in posts:
            entry = by_key.get(post.source_key)
            primary_confidence = 0.0
            if entry and entry.matches:
                primary = next((m for m in entry.matches if m.role == "primary"), entry.matches[0])
                primary_confidence = primary.confidence

            if not entry or not entry.matches:
                unmatched.append(post)
            elif primary_confidence < self._low_confidence_threshold:
                low_confidence.append(post)

            if post.saved_at >= recent_cutoff:
                recent.append(post)

        return {
            "unmatched": unmatched,
            "low_confidence": low_confidence,
            "recent": recent,
        }

    def discover(
        self,
        posts: list[NormalizedPost],
        classifications: list[PostClassification],
        taxonomy_version: str,
    ) -> tuple[list[DiscoveryCandidate], DiscoveryRunMetadata]:
        scope = self.select_scope(posts, classifications)

        selected_by_key: dict[str, NormalizedPost] = {}
        for group in scope.values():
            for post in group:
                selected_by_key[post.source_key] = post
        selected = list(selected_by_key.values())

        run = DiscoveryRunMetadata(
            taxonomy_version=taxonomy_version,
            backend="keyword_grouping",
            input_count=len(selected),
            diagnostics={
                "scope_counts": {
                    "unmatched": len(scope["unmatched"]),
                    "low_confidence": len(scope["low_confidence"]),
                    "recent": len(scope["recent"]),
                },
                "backlog_age_days": self._calculate_backlog_age_days(selected),
            },
        )

        if not selected:
            run.status = "success"
            run.finished_at = datetime.now(UTC)
            return [], run

        candidates: list[DiscoveryCandidate]
        if _bertopic_enabled() and find_spec("bertopic") is not None:
            try:
                candidates = self._discover_with_bertopic(selected, taxonomy_version, run.run_id)
                run.backend = "bertopic_clustering"
            except Exception as exc:
                if self._is_embedding_artifact_error(exc):
                    raise RuntimeError(
                        "Embedding model artifacts are unavailable due SSL/certificate trust issues. "
                        "Configure trusted corporate CA/proxy settings or set LOCAL_EMBEDDING_MODEL_PATH "
                        "to a readable local model path."
                    ) from exc
                run.diagnostics["fallback_reason"] = str(exc)
                candidates = self._discover_with_keyword_grouping(selected, taxonomy_version, run.run_id)
        else:
            candidates = self._discover_with_keyword_grouping(selected, taxonomy_version, run.run_id)

        run.candidate_count = len(candidates)
        run.status = "success"
        run.finished_at = datetime.now(UTC)
        return candidates, run

    def persist(
        self,
        candidates: list[DiscoveryCandidate],
        run: DiscoveryRunMetadata,
        run_path,
        candidates_path,
    ) -> None:
        append_discovery_run_metadata(run_path, run)
        append_discovery_candidates(candidates_path, candidates)

    def _discover_with_bertopic(
        self,
        posts: list[NormalizedPost],
        taxonomy_version: str,
        run_id: str,
    ) -> list[DiscoveryCandidate]:
        from bertopic import BERTopic
        from sklearn.feature_extraction.text import CountVectorizer

        docs = [f"{post.title or ''} {post.content}" for post in posts]
        vectorizer = CountVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1)
        embedding_model = self._resolve_embedding_model()

        representation_model = build_representation_model(
            RefinementConfig(
                use_keybert_inspired=True,
                use_mmr=True,
                use_llama_cpp=bool(self._llama_cpp_model_path),
                llama_cpp_model_path=(
                    Path(self._llama_cpp_model_path) if self._llama_cpp_model_path else None
                ),
            )
        )

        topic_model = BERTopic(
            embedding_model=embedding_model,
            vectorizer_model=vectorizer,
            representation_model=representation_model,
            calculate_probabilities=True,
            min_topic_size=2,
            verbose=False,
        )

        topics, probabilities = topic_model.fit_transform(docs)

        bucket: dict[int, list[int]] = {}
        for idx, topic_id in enumerate(topics):
            if topic_id == -1:
                continue
            bucket.setdefault(int(topic_id), []).append(idx)

        candidates: list[DiscoveryCandidate] = []
        for topic_id, indices in bucket.items():
            terms = topic_model.get_topic(topic_id) or []
            keywords = [term for term, _ in terms[:6]]
            label = ", ".join(keywords[:3]) if keywords else f"cluster-{topic_id}"

            confidence_values: list[float] = []
            if probabilities is not None:
                for idx in indices:
                    row = probabilities[idx]
                    if len(row) > topic_id:
                        confidence_values.append(float(row[topic_id]))
            confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0.5

            candidates.append(
                DiscoveryCandidate(
                    run_id=run_id,
                    taxonomy_version=taxonomy_version,
                    label=label,
                    keywords=keywords,
                    evidence_source_keys=[posts[idx].source_key for idx in indices],
                    confidence=round(confidence, 4),
                )
            )

        return sorted(candidates, key=lambda item: (len(item.evidence_source_keys), item.confidence), reverse=True)

    def _discover_with_keyword_grouping(
        self,
        posts: list[NormalizedPost],
        taxonomy_version: str,
        run_id: str,
    ) -> list[DiscoveryCandidate]:
        buckets: dict[str, list[NormalizedPost]] = {}
        for post in posts:
            tokens = [tok.lower() for tok in (post.title or "").split() if len(tok) > 3]
            key = tokens[0] if tokens else "general"
            buckets.setdefault(key, []).append(post)

        results: list[DiscoveryCandidate] = []
        for key, grouped in buckets.items():
            if len(grouped) < 2:
                continue
            keywords = sorted({tok.lower() for post in grouped for tok in post.content.split() if len(tok) > 4})[:6]
            results.append(
                DiscoveryCandidate(
                    run_id=run_id,
                    taxonomy_version=taxonomy_version,
                    label=key,
                    keywords=keywords,
                    evidence_source_keys=[post.source_key for post in grouped],
                    confidence=0.5,
                )
            )

        return results

    @staticmethod
    def _calculate_backlog_age_days(posts: list[NormalizedPost]) -> int:
        if not posts:
            return 0
        oldest = min(post.saved_at for post in posts)
        now = datetime.now(UTC)
        return max((now - oldest).days, 0)

    def _resolve_embedding_model(self) -> str:
        if not self._local_embedding_model_path:
            return "sentence-transformers/all-MiniLM-L6-v2"

        model_path = Path(self._local_embedding_model_path)
        if not model_path.exists():
            raise ValueError(
                f"LOCAL_EMBEDDING_MODEL_PATH is invalid: '{model_path}'. "
                "File or directory does not exist."
            )
        if not model_path.is_file() and not model_path.is_dir():
            raise ValueError(
                f"LOCAL_EMBEDDING_MODEL_PATH is invalid: '{model_path}'. "
                "Expected a readable file or directory."
            )

        try:
            if model_path.is_file():
                with model_path.open("rb"):
                    pass
        except OSError as exc:
            raise ValueError(
                f"LOCAL_EMBEDDING_MODEL_PATH is unreadable: '{model_path}'."
            ) from exc

        return str(model_path)

    @staticmethod
    def _is_embedding_artifact_error(exc: Exception) -> bool:
        lowered = str(exc).lower()
        markers = [
            "certificate_verify_failed",
            "ssl",
            "certificate",
            "huggingface",
            "adapter_config",
            "sentence-transformers",
        ]
        return any(marker in lowered for marker in markers)
