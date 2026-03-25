from __future__ import annotations

import os
import re
from importlib.util import find_spec
from collections.abc import Iterable
from datetime import datetime, timezone

from shared.models import ClassificationRunMetadata, PostClassification, TopicMatch
from shared.schemas import NormalizedPost
from shared.taxonomy import TaxonomyConfig, TopicDefinition


_TOKEN_RE = re.compile(r"[a-z0-9_]+")


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


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


def _topic_similarity(content: str, topic: TopicDefinition) -> float:
    content_tokens = _tokens(content)
    if not content_tokens:
        return 0.0

    keyword_tokens: set[str] = set()
    for word in [topic.name, *topic.keywords]:
        keyword_tokens.update(_tokens(word))

    if not keyword_tokens:
        return 0.0

    overlap = len(content_tokens.intersection(keyword_tokens))
    return overlap / max(len(keyword_tokens), 1)


class TaxonomyAssigner:
    """Stable taxonomy assignment with BERTopic-first, deterministic fallback scoring."""

    def __init__(self, min_similarity: float | None = None, secondary_min_similarity: float | None = None) -> None:
        self._min_similarity_override = min_similarity
        self._secondary_min_similarity_override = secondary_min_similarity

    def assign(
        self,
        posts: Iterable[NormalizedPost],
        taxonomy: TaxonomyConfig,
    ) -> tuple[list[PostClassification], ClassificationRunMetadata]:
        min_similarity = self._min_similarity_override or taxonomy.zeroshot_min_similarity
        secondary_similarity = self._secondary_min_similarity_override or taxonomy.secondary_min_similarity

        run = ClassificationRunMetadata(
            taxonomy_version=taxonomy.taxonomy_version,
            backend="keyword_fallback",
            zeroshot_min_similarity=min_similarity,
            secondary_min_similarity=secondary_similarity,
        )

        post_list = list(posts)
        if _bertopic_enabled() and find_spec("bertopic") is not None:
            try:
                results = self._assign_with_bertopic(post_list, taxonomy, min_similarity, secondary_similarity)
                run.backend = "bertopic_zeroshot"
                run.matched_count = sum(1 for item in results if item.matches)
                run.processed_count = len(results)
                run.status = "success"
                run.finished_at = datetime.now(timezone.utc)
                run.diagnostics = {
                    "unmatched_count": run.processed_count - run.matched_count,
                    "strategy": "bertopic zeroshot topic list",
                }
                return results, run
            except Exception as exc:
                run.diagnostics = {"fallback_reason": str(exc)}

        results: list[PostClassification] = []

        for post in post_list:
            scored = [
                (
                    topic,
                    _topic_similarity(f"{post.title or ''} {post.content}", topic),
                )
                for topic in taxonomy.topics
            ]
            scored.sort(key=lambda item: item[1], reverse=True)

            matches: list[TopicMatch] = []
            if scored and scored[0][1] >= min_similarity:
                primary_topic, primary_score = scored[0]
                matches.append(
                    TopicMatch(
                        topic_slug=primary_topic.slug,
                        topic_name=primary_topic.name,
                        confidence=round(primary_score, 4),
                        role="primary",
                    )
                )

                for topic, score in scored[1:]:
                    if score >= secondary_similarity:
                        matches.append(
                            TopicMatch(
                                topic_slug=topic.slug,
                                topic_name=topic.name,
                                confidence=round(score, 4),
                                role="secondary",
                            )
                        )

            if matches:
                run.matched_count += 1

            results.append(
                PostClassification(
                    source_key=post.source_key,
                    taxonomy_version=taxonomy.taxonomy_version,
                    matches=matches,
                )
            )

        run.processed_count = len(results)
        run.status = "success"
        run.finished_at = datetime.now(timezone.utc)
        run.diagnostics = {
            "unmatched_count": run.processed_count - run.matched_count,
            "strategy": "deterministic keyword overlap fallback",
        }
        return results, run

    def _assign_with_bertopic(
        self,
        posts: list[NormalizedPost],
        taxonomy: TaxonomyConfig,
        min_similarity: float,
        secondary_similarity: float,
    ) -> list[PostClassification]:
        from bertopic import BERTopic

        docs = [f"{post.title or ''} {post.content}" for post in posts]
        topic_model = BERTopic(
            zeroshot_topic_list=[topic.name for topic in taxonomy.topics],
            zeroshot_min_similarity=min_similarity,
            calculate_probabilities=True,
            embedding_model=_build_embedding_model(),
            verbose=False,
        )
        topics, probabilities = topic_model.fit_transform(docs)

        results: list[PostClassification] = []
        for idx, post in enumerate(posts):
            matches: list[TopicMatch] = []
            row = probabilities[idx] if probabilities is not None else None
            if row is not None and len(row) > 0:
                ranked = sorted(enumerate(row), key=lambda item: float(item[1]), reverse=True)
                if ranked and float(ranked[0][1]) >= min_similarity:
                    primary_topic_idx, primary_score = ranked[0]
                    primary_name = topic_model.get_topic_info(primary_topic_idx).iloc[0]["Name"]
                    matches.append(
                        TopicMatch(
                            topic_slug=primary_name.lower().replace(" ", "-"),
                            topic_name=primary_name,
                            confidence=round(float(primary_score), 4),
                            role="primary",
                        )
                    )

                    for topic_idx, score in ranked[1:]:
                        if float(score) >= secondary_similarity:
                            name = topic_model.get_topic_info(topic_idx).iloc[0]["Name"]
                            matches.append(
                                TopicMatch(
                                    topic_slug=name.lower().replace(" ", "-"),
                                    topic_name=name,
                                    confidence=round(float(score), 4),
                                    role="secondary",
                                )
                            )
            elif topics[idx] != -1:
                name = topic_model.get_topic_info(topics[idx]).iloc[0]["Name"]
                matches.append(
                    TopicMatch(
                        topic_slug=name.lower().replace(" ", "-"),
                        topic_name=name,
                        confidence=1.0,
                        role="primary",
                    )
                )

            results.append(
                PostClassification(
                    source_key=post.source_key,
                    taxonomy_version=taxonomy.taxonomy_version,
                    matches=matches,
                )
            )

        return results
