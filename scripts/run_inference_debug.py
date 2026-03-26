from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from local_sync.config import LocalSyncConfig
from local_sync.taxonomy_assignment import TaxonomyAssigner
from local_sync.topic_discovery import TopicDiscoveryPipeline
from shared.schemas import NormalizedPost
from shared.taxonomy import load_taxonomy, validate_taxonomy


def _latest_export_file(export_dir: Path) -> Path:
    files = sorted(export_dir.glob("batch_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise FileNotFoundError(
            f"No export batches found in {export_dir}. Run one sync first or pass --input-export."
        )
    return files[0]


def _load_posts_from_export(path: Path, limit: int | None) -> list[NormalizedPost]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_posts = payload.get("posts", [])
    posts = [NormalizedPost.model_validate(item) for item in raw_posts]
    if limit is not None:
        return posts[: max(limit, 0)]
    return posts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run taxonomy assignment + discovery (embedding path) from an exported batch only."
    )
    parser.add_argument("--env-path", default=".env", help="Root env file path used by LocalSyncConfig.")
    parser.add_argument("--input-export", default="", help="Path to exported batch JSON.")
    parser.add_argument("--limit", type=int, default=10, help="Max posts from export to process.")
    parser.add_argument("--print-candidates", action="store_true", help="Print candidate labels/keywords.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = LocalSyncConfig.from_env(args.env_path)

    export_path = Path(args.input_export) if args.input_export else _latest_export_file(config.export_dir)
    posts = _load_posts_from_export(export_path, args.limit)
    if not posts:
        print(json.dumps({"status": "failed", "reason": "no_posts_in_export", "export_path": str(export_path)}))
        return 1

    taxonomy = load_taxonomy(config.taxonomy_path)
    validate_taxonomy(taxonomy)

    assigner = TaxonomyAssigner(
        min_similarity=config.zeroshot_min_similarity,
        secondary_min_similarity=config.secondary_min_similarity,
    )
    classifications, run_metadata = assigner.assign(posts, taxonomy)

    discovery = TopicDiscoveryPipeline(
        low_confidence_threshold=config.discovery_low_confidence_threshold,
        recent_window_days=config.discovery_recent_window_days,
        llama_cpp_model_path=str(config.llama_cpp_model_path) if config.llama_cpp_model_path else None,
        local_embedding_model_path=(
            str(config.local_embedding_model_path) if config.local_embedding_model_path else None
        ),
    )
    candidates, discovery_run = discovery.discover(
        posts,
        classifications,
        taxonomy_version=taxonomy.taxonomy_version,
    )

    matched = sum(1 for item in classifications if item.matches)
    summary: dict[str, Any] = {
        "status": "ok",
        "export_path": str(export_path),
        "processed_posts": len(posts),
        "classification_run_id": run_metadata.run_id,
        "classification_backend": run_metadata.backend,
        "classification_matched_count": matched,
        "discovery_run_id": discovery_run.run_id,
        "discovery_backend": discovery_run.backend,
        "discovery_candidate_count": len(candidates),
    }
    if args.print_candidates:
        summary["candidates"] = [
            {
                "id": item.candidate_id,
                "label": item.label,
                "confidence": item.confidence,
                "keywords": item.keywords,
                "evidence_count": len(item.evidence_source_keys),
            }
            for item in candidates
        ]

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
