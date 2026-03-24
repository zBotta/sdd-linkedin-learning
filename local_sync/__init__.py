"""Local sync package for LinkedIn saved posts ingestion."""

from .config import LocalSyncConfig
from .sync_agent import SyncAgent

__all__ = ["LocalSyncConfig", "SyncAgent"]
