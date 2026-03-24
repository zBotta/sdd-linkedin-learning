from __future__ import annotations

import json
from pathlib import Path

from local_sync.config import LocalSyncConfig
from local_sync.sync_agent import SyncAgent


class FixedScraper:
    def fetch_saved_posts(self, limit: int = 100) -> list[dict]:
        _ = limit
        return [
            {
                "source_post_id": "post-1",
                "title": "Rust ownership",
                "content": "cargo and ownership tips",
                "saved_at": "2026-03-24T10:00:00+00:00",
            },
            {
                "source_post_id": "post-2",
                "title": "MCP server",
                "content": "tool server for model context protocol",
                "saved_at": "2026-03-24T10:01:00+00:00",
            },
        ]


def _taxonomy_file(path: Path) -> Path:
    tax = path / "topics.yaml"
    tax.write_text(
        """
taxonomy_version: v1.2.3
zeroshot_min_similarity: 0.2
secondary_min_similarity: 0.35
topics:
  - slug: rust
    name: Rust
    keywords: [rust, cargo, ownership]
  - slug: mcp
    name: MCP
    keywords: [mcp, model context protocol, server, tool]
""".strip(),
        encoding="utf-8",
    )
    return tax


def _run_once(tmp_path: Path) -> dict[str, object]:
    taxonomy_path = _taxonomy_file(tmp_path)
    config = LocalSyncConfig(
        state_path=tmp_path / "state" / "sync_state.json",
        export_dir=tmp_path / "exports",
        export_enabled=True,
        linkedin_profile_dir=tmp_path / "profile",
        linkedin_headless=False,
        linkedin_session_wait_seconds=30,
        push_enabled=False,
        cloud_api_base_url="",
        cloud_ingest_token="",
        push_timeout_seconds=5,
        taxonomy_path=taxonomy_path,
        zeroshot_min_similarity=None,
        secondary_min_similarity=None,
        classification_runs_path=tmp_path / "state" / "classification_runs.jsonl",
    )
    return SyncAgent(config=config, scraper=FixedScraper()).run_once()


def test_stable_classification_is_reproducible(tmp_path: Path) -> None:
    run1_root = tmp_path / "phase2_run1"
    run2_root = tmp_path / "phase2_run2"
    run1_root.mkdir(parents=True, exist_ok=True)
    run2_root.mkdir(parents=True, exist_ok=True)

    first = _run_once(run1_root)
    second = _run_once(run2_root)

    first_export = json.loads(Path(str(first["export_path"])).read_text(encoding="utf-8"))
    second_export = json.loads(Path(str(second["export_path"])).read_text(encoding="utf-8"))

    first_map = {
        item["source_key"]: [(m["topic_slug"], m["role"], m["confidence"]) for m in item["matches"]]
        for item in first_export["classifications"]
    }
    second_map = {
        item["source_key"]: [(m["topic_slug"], m["role"], m["confidence"]) for m in item["matches"]]
        for item in second_export["classifications"]
    }

    assert first_map == second_map
