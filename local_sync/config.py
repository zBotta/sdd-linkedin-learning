from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _load_env_file(env_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not env_path.exists():
        return values

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


@dataclass(slots=True)
class LocalSyncConfig:
    state_path: Path
    export_dir: Path
    export_enabled: bool
    linkedin_profile_dir: Path
    linkedin_headless: bool
    linkedin_session_wait_seconds: int
    push_enabled: bool
    cloud_api_base_url: str
    cloud_ingest_token: str
    push_timeout_seconds: int
    linkedin_stop_on_first_seen: bool = True
    full_rescrape: bool = False
    taxonomy_path: Path = Path("topics.yaml")
    zeroshot_min_similarity: float | None = None
    secondary_min_similarity: float | None = None
    classification_runs_path: Path = Path(".state/classification_runs.jsonl")
    discovery_low_confidence_threshold: float = 0.45
    discovery_recent_window_days: int = 7
    discovery_runs_path: Path = Path(".state/discovery_runs.jsonl")
    discovery_candidates_path: Path = Path(".state/topic_candidates.jsonl")
    llama_cpp_model_path: Path | None = None
    local_embedding_model_path: Path | None = None

    @classmethod
    def from_env(cls, env_path: str | Path = ".env") -> "LocalSyncConfig":
        env_file_values = _load_env_file(Path(env_path))

        def get(key: str, default: str) -> str:
            return os.getenv(key, env_file_values.get(key, default))

        state_path = Path(get("LOCAL_SYNC_STATE_PATH", ".state/sync_state.json"))
        export_dir = Path(get("LOCAL_SYNC_EXPORT_DIR", "exports"))
        linkedin_profile_dir = Path(get("LINKEDIN_PROFILE_DIR", ".state/playwright-profile"))

        return cls(
            state_path=state_path,
            export_dir=export_dir,
            export_enabled=_parse_bool(get("LOCAL_SYNC_EXPORT_ENABLED", "true"), True),
            linkedin_profile_dir=linkedin_profile_dir,
            linkedin_headless=_parse_bool(get("LINKEDIN_HEADLESS", "false"), False),
            linkedin_session_wait_seconds=int(get("LINKEDIN_SESSION_WAIT_SECONDS", "120")),
            linkedin_stop_on_first_seen=_parse_bool(
                get("LINKEDIN_STOP_ON_FIRST_SEEN", "true"),
                True,
            ),
            full_rescrape=_parse_bool(get("LOCAL_SYNC_FULL_RESCRAPE", "false"), False),
            push_enabled=_parse_bool(get("PUSH_ENABLED", "false"), False),
            cloud_api_base_url=get("CLOUD_API_BASE_URL", ""),
            cloud_ingest_token=get("CLOUD_INGEST_TOKEN", ""),
            push_timeout_seconds=int(get("PUSH_TIMEOUT_SECONDS", "20")),
            taxonomy_path=Path(get("TAXONOMY_PATH", "topics.yaml")),
            zeroshot_min_similarity=(
                float(get("ZEROSHOT_MIN_SIMILARITY", ""))
                if get("ZEROSHOT_MIN_SIMILARITY", "")
                else None
            ),
            secondary_min_similarity=(
                float(get("SECONDARY_MIN_SIMILARITY", ""))
                if get("SECONDARY_MIN_SIMILARITY", "")
                else None
            ),
            classification_runs_path=Path(
                get("CLASSIFICATION_RUNS_PATH", ".state/classification_runs.jsonl")
            ),
            discovery_low_confidence_threshold=float(
                get("DISCOVERY_LOW_CONFIDENCE_THRESHOLD", "0.45")
            ),
            discovery_recent_window_days=int(get("DISCOVERY_RECENT_WINDOW_DAYS", "7")),
            discovery_runs_path=Path(get("DISCOVERY_RUNS_PATH", ".state/discovery_runs.jsonl")),
            discovery_candidates_path=Path(
                get("DISCOVERY_CANDIDATES_PATH", ".state/topic_candidates.jsonl")
            ),
            llama_cpp_model_path=(
                Path(get("LLAMA_CPP_MODEL_PATH", ""))
                if get("LLAMA_CPP_MODEL_PATH", "")
                else None
            ),
            local_embedding_model_path=(
                Path(get("LOCAL_EMBEDDING_MODEL_PATH", ""))
                if get("LOCAL_EMBEDDING_MODEL_PATH", "")
                else None
            ),
        )
