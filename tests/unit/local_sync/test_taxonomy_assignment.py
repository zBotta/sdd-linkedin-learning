from __future__ import annotations

from local_sync.preprocessing import normalize_post
from local_sync.taxonomy_assignment import TaxonomyAssigner
from shared.taxonomy import TaxonomyConfig


def _taxonomy() -> TaxonomyConfig:
    return TaxonomyConfig.model_validate(
        {
            "taxonomy_version": "v1",
            "zeroshot_min_similarity": 0.2,
            "secondary_min_similarity": 0.3,
            "topics": [
                {
                    "slug": "rust",
                    "name": "Rust",
                    "keywords": ["rust", "cargo", "ownership"],
                },
                {
                    "slug": "mcp",
                    "name": "MCP",
                    "keywords": ["mcp", "server", "tool"],
                },
            ],
        }
    )


def test_primary_topic_is_selected_when_above_threshold() -> None:
    post = normalize_post(
        {
            "source_post_id": "1",
            "title": "Rust async",
            "content": "cargo and ownership patterns",
            "saved_at": "2026-03-24T10:00:00+00:00",
        }
    )

    assigner = TaxonomyAssigner()
    classifications, run = assigner.assign([post], _taxonomy())

    assert run.status == "success"
    assert run.matched_count == 1
    assert classifications[0].matches[0].topic_slug == "rust"
    assert classifications[0].matches[0].role == "primary"


def test_secondary_topics_require_stricter_threshold() -> None:
    post = normalize_post(
        {
            "source_post_id": "2",
            "title": "Rust MCP tool",
            "content": "rust tool server and cargo",
            "saved_at": "2026-03-24T10:00:00+00:00",
        }
    )

    assigner = TaxonomyAssigner(min_similarity=0.2, secondary_min_similarity=0.3)
    classifications, _ = assigner.assign([post], _taxonomy())
    roles = [match.role for match in classifications[0].matches]

    assert roles[0] == "primary"
    assert roles.count("secondary") >= 1


def test_no_match_when_below_similarity_threshold() -> None:
    post = normalize_post(
        {
            "source_post_id": "3",
            "title": "Gardening",
            "content": "soil and watering plans",
            "saved_at": "2026-03-24T10:00:00+00:00",
        }
    )

    assigner = TaxonomyAssigner(min_similarity=0.9)
    classifications, run = assigner.assign([post], _taxonomy())

    assert classifications[0].matches == []
    assert run.matched_count == 0
