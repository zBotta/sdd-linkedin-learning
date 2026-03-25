from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from shared.schemas import NormalizedPost


class StateStore:
    """Persist and query sync checkpoints for incremental local runs."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._state = self._load()

    @staticmethod
    def _empty_state() -> dict[str, object]:
        return {
            "seen_source_keys": [],
            "last_run_at": None,
            "last_batch_id": None,
        }

    def _load(self) -> dict[str, object]:
        if not self._path.exists():
            return self._empty_state()

        try:
            with self._path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (json.JSONDecodeError, OSError, ValueError):
            return self._empty_state()

        if not isinstance(data, dict):
            return self._empty_state()

        seen = data.get("seen_source_keys", [])
        if not isinstance(seen, list):
            seen = []

        cleaned_seen = sorted({str(item).strip() for item in seen if str(item).strip()})
        return {
            "seen_source_keys": cleaned_seen,
            "last_run_at": data.get("last_run_at"),
            "last_batch_id": data.get("last_batch_id"),
        }

    @property
    def seen_source_keys(self) -> set[str]:
        return set(self._state.get("seen_source_keys", []))

    def filter_new(self, posts: list[NormalizedPost]) -> list[NormalizedPost]:
        seen = self.seen_source_keys
        return [post for post in posts if post.source_key not in seen]

    def mark_synced(self, posts: list[NormalizedPost], batch_id: str) -> None:
        seen = self.seen_source_keys
        for post in posts:
            seen.add(post.source_key)

        self._state["seen_source_keys"] = sorted(seen)
        self._state["last_run_at"] = datetime.now(UTC).isoformat()
        self._state["last_batch_id"] = batch_id
        self._save()

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as handle:
            json.dump(self._state, handle, indent=2)
