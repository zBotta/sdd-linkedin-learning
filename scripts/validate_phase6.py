from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import sys
from typing import Any, Callable
import uuid

# Ensure imports resolve when executed as: uv run python scripts/validate_phase6.py
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from local_sync.config import LocalSyncConfig
from local_sync.sync_agent import SyncAgent
from tests.integration.helpers import (
    ValidationEvidenceWriter,
    probe_required_services,
    run_e2e_with_fallback,
    run_podman_deployment,
    validate_embedding_reliability,
    verify_sql_tables,
)

DEFAULT_COMPOSE_FILE = Path("cloud/docker-compose.yml")
DEFAULT_OUTPUT_PATH = Path(".state/validation/phase6_evidence.jsonl")
US1_REQUIRED_STAGES = ("deployment", "readiness")
US2_REQUIRED_STAGES = ("e2e", "sql")
US3_REQUIRED_STAGES = ("embedding",)
ROOT_ENV_FILE = REPO_ROOT / ".env"
CLOUD_ENV_FILE = REPO_ROOT / "cloud" / ".env"


def parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def trace(message: str) -> None:
    print(f"[phase6] {message}", flush=True)


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def load_runtime_defaults() -> dict[str, str]:
    defaults = load_env_file(ROOT_ENV_FILE)
    defaults.update(load_env_file(CLOUD_ENV_FILE))
    return defaults


def maybe_warn_windows_data_dir(defaults: dict[str, str]) -> None:
    if os.name != "nt":
        return
    data_dir = (defaults.get("DATA_DIR") or "").strip()
    if data_dir.startswith("/"):
        trace(
            "Preflight warning: cloud/.env DATA_DIR is a Linux-style absolute path "
            f"('{data_dir}'). On local Windows Podman runs this commonly fails with "
            "permission denied. Set DATA_DIR to a writable local path, for example "
            "'./.state/cloud-data'."
        )


def _is_missing_or_placeholder(value: str | None) -> bool:
    if value is None:
        return True
    normalized = value.strip().lower()
    return normalized in {"", "replace-me", "changeme", "change-me"}


def _is_placeholder_base_url(value: str | None) -> bool:
    if value is None:
        return True
    normalized = value.strip().lower()
    return normalized in {"", "https://example.com", "http://example.com"}


def _resolve_cloud_data_dir_to_host_path(data_dir_raw: str, repo_root: Path) -> Path:
    value = (data_dir_raw or "").strip()
    if not value:
        return repo_root / ".state" / "cloud-data"
    if value.startswith("./") or value.startswith(".\\"):
        return (repo_root / "cloud" / value).resolve()
    if value.startswith("../") or value.startswith("..\\"):
        return (repo_root / "cloud" / value).resolve()
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    return (repo_root / value).resolve()


def resolve_sql_db_path_for_host(
    sql_db_path: str,
    *,
    data_dir_raw: str,
    repo_root: Path,
) -> Path:
    raw = (sql_db_path or "").strip()
    normalized = raw.replace("\\", "/")
    if normalized.startswith("/data/"):
        suffix = normalized[len("/data/") :]
        return _resolve_cloud_data_dir_to_host_path(data_dir_raw, repo_root) / suffix
    return Path(raw)


def validate_preflight_configuration(
    args: argparse.Namespace,
    root_values: dict[str, str],
    cloud_values: dict[str, str],
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    include_us3 = bool(getattr(args, "include_us3", False))
    include_us2 = bool(getattr(args, "include_us2", False))

    if not ROOT_ENV_FILE.exists():
        errors.append(
            f"Missing required env file: {ROOT_ENV_FILE}. Create it from .env.example and fill required values."
        )
    if not CLOUD_ENV_FILE.exists():
        errors.append(
            f"Missing required env file: {CLOUD_ENV_FILE}. Create it from cloud/.env.example and fill required values."
        )
    # Enforce deterministic config: for deployment validation, shell env should not
    # override .env values silently for critical auth/push settings.
    env_lock_keys = (
        "PUSH_ENABLED",
        "CLOUD_API_BASE_URL",
        "CLOUD_INGEST_TOKEN",
        "INGEST_API_TOKEN",
        "UI_ACCESS_PASSWORD",
    )
    for key in env_lock_keys:
        shell_value = os.getenv(key)
        root_value = root_values.get(key)
        cloud_value = cloud_values.get(key)
        file_value = cloud_value if cloud_value is not None else root_value
        if shell_value is None or file_value is None:
            continue
        if shell_value != file_value:
            errors.append(
                f"Environment override detected for {key}: shell='{shell_value}' "
                f"!= .env value='{file_value}'. Unset the shell variable and use .env/cloud/.env values."
            )

    ingest_token = cloud_values.get("INGEST_API_TOKEN")
    if _is_missing_or_placeholder(ingest_token):
        errors.append(
            "cloud/.env -> INGEST_API_TOKEN is missing or still placeholder. Set a real token value."
        )

    ui_password = cloud_values.get("UI_ACCESS_PASSWORD")
    if _is_missing_or_placeholder(ui_password):
        errors.append(
            "cloud/.env -> UI_ACCESS_PASSWORD is missing or still placeholder. Set a real password value."
        )

    data_dir = (cloud_values.get("DATA_DIR") or "").strip()
    cloud_db_path_value = (cloud_values.get("CLOUD_DB_PATH") or "").strip()
    if not data_dir:
        errors.append(
            "cloud/.env -> DATA_DIR is missing. Set it to a writable path (example: ./.state/cloud-data)."
        )
    elif "#" in data_dir:
        errors.append(
            f"cloud/.env -> DATA_DIR contains '#': '{data_dir}'. "
            "Remove inline comments from the DATA_DIR line (put comments on separate lines)."
        )
    elif os.name == "nt" and data_dir.startswith("/"):
        errors.append(
            f"cloud/.env -> DATA_DIR='{data_dir}' is Linux-style and will fail on Windows. "
            "Use a local writable path (example: ./.state/cloud-data)."
        )
    elif data_dir.startswith("./"):
        warnings.append(
            f"cloud/.env -> DATA_DIR='{data_dir}' is relative to the cloud/ directory. "
            "If you want repository-root .state, prefer '../.state/cloud-data'."
        )
    if include_us2 and cloud_db_path_value and not cloud_db_path_value.replace("\\", "/").startswith("/data/"):
        errors.append(
            "cloud/.env -> CLOUD_DB_PATH must be under /data for US2 SQL verification "
            f"(current: '{cloud_db_path_value}'). Use '/data/library.db' so API writes to the mounted DATA_DIR volume."
        )
    root_data_dir = (root_values.get("DATA_DIR") or "").strip()
    if not root_data_dir:
        warnings.append(
            ".env -> DATA_DIR is empty. Consider setting it to match cloud/.env DATA_DIR for consistency."
        )
    elif data_dir and root_data_dir != data_dir:
        warnings.append(
            ".env/cloud/.env -> DATA_DIR values differ "
            f"(.env='{root_data_dir}' vs cloud/.env='{data_dir}'). "
            "Use the same writable path to avoid environment drift."
        )
    root_cloud_db_path = (root_values.get("CLOUD_DB_PATH") or "").strip()
    cloud_cloud_db_path = (cloud_values.get("CLOUD_DB_PATH") or "").strip()
    if root_cloud_db_path and cloud_cloud_db_path and root_cloud_db_path != cloud_cloud_db_path:
        message = (
            ".env/cloud/.env CLOUD_DB_PATH mismatch "
            f"(.env='{root_cloud_db_path}' vs cloud/.env='{cloud_cloud_db_path}'). "
            "Align them or pass --sql-db-path explicitly for host verification."
        )
        if include_us2:
            errors.append(message)
        else:
            warnings.append(message)

    llama_path = (root_values.get("LLAMA_CPP_MODEL_PATH") or "").strip()
    if llama_path:
        if not Path(llama_path).exists():
            errors.append(
                f".env -> LLAMA_CPP_MODEL_PATH points to a non-existent path: {llama_path}. "
                "Fix the path or leave it empty to disable GGUF refinement."
            )
    else:
        warnings.append(
            ".env -> LLAMA_CPP_MODEL_PATH is empty (GGUF label refinement disabled)."
        )

    cloud_ingest_token = (cloud_values.get("INGEST_API_TOKEN") or "").strip()
    root_push_token = (root_values.get("CLOUD_INGEST_TOKEN") or "").strip()
    root_cloud_api_base_url = (root_values.get("CLOUD_API_BASE_URL") or "").strip()
    arg_push_api_base_url = str(getattr(args, "push_api_base_url", "")).strip()
    effective_push_api_base_url = arg_push_api_base_url or root_cloud_api_base_url
    push_enabled = parse_bool((root_values.get("PUSH_ENABLED") or "").strip(), False)
    if include_us2 and not push_enabled:
        errors.append(
            ".env -> PUSH_ENABLED=false. US2 requires real API push; set PUSH_ENABLED=true."
        )
    if include_us2 and _is_placeholder_base_url(effective_push_api_base_url):
        errors.append(
            ".env/args -> CLOUD_API_BASE_URL is empty/placeholder for US2. "
            "Set .env CLOUD_API_BASE_URL explicitly (example: http://127.0.0.1:8000) "
            "or pass --push-api-base-url."
        )
    if _is_missing_or_placeholder(root_push_token):
        if include_us2:
            errors.append(
                ".env -> CLOUD_INGEST_TOKEN is missing or placeholder; US2 E2E push requires it."
            )
        else:
            warnings.append(
                ".env -> CLOUD_INGEST_TOKEN is missing or placeholder; set it before running US2."
            )
    elif cloud_ingest_token and root_push_token != cloud_ingest_token:
        message = (
            ".env/cloud/.env token mismatch: CLOUD_INGEST_TOKEN (.env) "
            f"!= INGEST_API_TOKEN (cloud/.env). Ensure they are identical "
            "so local_sync push auth matches API auth."
        )
        if include_us2:
            errors.append(message)
        else:
            warnings.append(message)

    root_ui_password = (root_values.get("UI_ACCESS_PASSWORD") or "").strip()
    if root_ui_password and ui_password and root_ui_password != ui_password:
        warnings.append(
            ".env/cloud/.env UI_ACCESS_PASSWORD values do not match. "
            "Align them to avoid confusion between local and cloud runtime access."
        )

    embedding_online_available = parse_bool(
        str(getattr(args, "embedding_online_available", "false")),
        False,
    )
    embedding_fallback_path = (str(getattr(args, "embedding_fallback_path", "")).strip())

    if include_us3:
        if embedding_fallback_path:
            if not Path(embedding_fallback_path).exists():
                errors.append(
                    f".env -> LOCAL_EMBEDDING_MODEL_PATH is set but does not exist: {embedding_fallback_path}. "
                    "Set a valid local model path or clear it."
                )
        elif not embedding_online_available:
            errors.append(
                ".env -> LOCAL_EMBEDDING_MODEL_PATH is empty while US3 runs with "
                "VALIDATION_EMBEDDING_ONLINE_AVAILABLE=false. Set a valid local embedding model path "
                "(example: C:/Users/mbottari/.models/all-MiniLM-L6-v2_model.safetensors) "
                "or enable online embedding availability."
            )
    elif not embedding_fallback_path and not embedding_online_available:
        warnings.append(
            ".env -> LOCAL_EMBEDDING_MODEL_PATH is empty and online embedding is disabled. "
            "US3 will fail if enabled."
        )

    e2e_sample_limit = int(getattr(args, "e2e_sample_limit", 25))
    if e2e_sample_limit < 1:
        errors.append("--e2e-sample-limit must be >= 1.")
    test_e2e_sample_limit = getattr(args, "test_e2e_sample_limit", None)
    if test_e2e_sample_limit is not None and int(test_e2e_sample_limit) < 1:
        errors.append("--test-e2e-sample-limit must be >= 1 when provided.")

    return errors, warnings


def evaluate_mandatory_stage_outcomes(
    stage_status: dict[str, str],
    *,
    required_stages: tuple[str, ...],
) -> tuple[str, list[str]]:
    failed = [name for name in required_stages if stage_status.get(name) != "passed"]
    return ("failed", failed) if failed else ("passed", [])


def run_deployment_stage(
    *,
    compose_file: Path,
    project_root: Path,
    compose_command: str,
) -> dict[str, Any]:
    deployment = run_podman_deployment(
        compose_file=compose_file,
        project_directory=project_root,
        compose_command=compose_command,
    )
    return {
        "status": deployment.status,
        "metadata": {
            "command": deployment.command,
            "exit_code": deployment.exit_code,
            "stdout": deployment.stdout,
            "stderr": deployment.stderr,
            "compose_file": str(compose_file),
            "project_root": str(project_root),
            "compose_command": compose_command,
        },
    }


def run_readiness_stage(
    *,
    api_url: str,
    ui_url: str,
    api_token: str | None,
    timeout_seconds: int,
    interval_seconds: float,
) -> dict[str, Any]:
    probes = {"api": api_url, "ui": ui_url}
    headers_by_service: dict[str, dict[str, str]] = {}
    if api_token:
        headers_by_service["api"] = {"Authorization": f"Bearer {api_token}"}
    readiness_results = probe_required_services(
        probes,
        timeout_seconds=timeout_seconds,
        probe_interval_seconds=interval_seconds,
        request_headers_by_service=headers_by_service or None,
    )
    status = "passed" if all(r.status == "passed" for r in readiness_results.values()) else "failed"
    return {
        "status": status,
        "metadata": {
            "timeout_seconds": timeout_seconds,
            "interval_seconds": interval_seconds,
            "services": {name: asdict(result) for name, result in readiness_results.items()},
        },
    }


def run_sync_once(*, full_rescrape: bool, limit: int) -> dict[str, Any]:
    mode = "full-rescrape" if full_rescrape else "incremental"
    trace(f"US2/E2E: starting local_sync run (mode={mode}, limit={limit})")
    trace("US2/E2E: scraping saved LinkedIn posts, classifying, running BERTopic/discovery, and pushing to API")
    previous = os.getenv("LOCAL_SYNC_FULL_RESCRAPE")
    push_base_url_override = os.getenv("PHASE6_PUSH_API_BASE_URL", "").strip()
    os.environ["LOCAL_SYNC_FULL_RESCRAPE"] = "true" if full_rescrape else "false"
    if push_base_url_override:
        previous_cloud_api_base_url = os.getenv("CLOUD_API_BASE_URL")
        os.environ["CLOUD_API_BASE_URL"] = push_base_url_override
    else:
        previous_cloud_api_base_url = None
    try:
        config = LocalSyncConfig.from_env(ROOT_ENV_FILE)
        agent = SyncAgent(config=config)
        result = agent.run_once(limit=limit)
    finally:
        if previous is None:
            os.environ.pop("LOCAL_SYNC_FULL_RESCRAPE", None)
        else:
            os.environ["LOCAL_SYNC_FULL_RESCRAPE"] = previous
        if push_base_url_override:
            if previous_cloud_api_base_url is None:
                os.environ.pop("CLOUD_API_BASE_URL", None)
            else:
                os.environ["CLOUD_API_BASE_URL"] = previous_cloud_api_base_url

    push_result = result.get("push_result", {})
    push_status_code = push_result.get("status_code")
    push_message = str(push_result.get("message", ""))
    trace(
        "US2/E2E: run completed "
        f"(scraped={result.get('scraped_count', 0)}, new={result.get('new_count', 0)}, "
        f"classification_run_id={result.get('classification_run_id')}, "
        f"discovery_run_id={result.get('discovery_run_id')}, "
        f"topic_runs_registered={result.get('topic_runs_registered_count', 0)}, "
        f"push_applied={push_result.get('applied', False)}, "
        f"push_status_code={push_status_code}, push_message={push_message})"
    )
    return {
        "scraped_count": int(result.get("scraped_count", 0)),
        "new_count": int(result.get("new_count", 0)),
        "processed_count": int(result.get("new_count", 0)),
        "push_applied": bool(push_result.get("applied", False)),
        "push_status_code": push_status_code,
        "push_message": push_message,
        "topic_runs_registered_count": int(result.get("topic_runs_registered_count", 0)),
        "topic_runs_registration": result.get("topic_runs_registration", []),
        "classification_run_id": result.get("classification_run_id"),
        "discovery_run_id": result.get("discovery_run_id"),
        "discovery_candidate_count": int(result.get("discovery_candidate_count", 0)),
    }


def run_e2e_stage(
    *,
    sample_limit: int,
    sync_runner: Callable[..., dict[str, Any]],
    allow_full_rescrape_fallback: bool = True,
) -> dict[str, Any]:
    status: str
    mode: str
    scraped_count: int
    new_count: int
    processed_count: int
    discovery_candidate_count: int
    push_applied: bool

    if allow_full_rescrape_fallback:
        trace("US2/E2E: orchestrating incremental run with automatic full-rescrape fallback when needed")
        e2e = run_e2e_with_fallback(
            lambda *, full_rescrape: sync_runner(full_rescrape=full_rescrape, limit=sample_limit)
        )
        status = e2e.status
        mode = e2e.mode
        scraped_count = e2e.scraped_count
        new_count = e2e.new_count
        processed_count = e2e.processed_count
        discovery_candidate_count = e2e.discovery_candidate_count
        push_applied = e2e.push_applied
        push_status_code = None
        push_message = ""
    else:
        trace("US2/E2E: running incremental-only mode (full-rescrape fallback disabled)")
        first = sync_runner(full_rescrape=False, limit=sample_limit)
        processed_count = int(first.get("processed_count", first.get("new_count", 0)))
        push_applied = bool(first.get("push_applied", False))
        push_status_code = first.get("push_status_code")
        push_message = str(first.get("push_message", ""))
        topic_runs_registered_count = int(first.get("topic_runs_registered_count", 0))
        topic_runs_registration = first.get("topic_runs_registration", [])
        status = "passed" if processed_count >= 1 and push_applied else "failed"
        mode = "incremental_only_no_fallback"
        scraped_count = int(first.get("scraped_count", 0))
        new_count = int(first.get("new_count", 0))
        discovery_candidate_count = int(first.get("discovery_candidate_count", 0))
    if allow_full_rescrape_fallback:
        topic_runs_registered_count = 0
        topic_runs_registration = []
    trace(
        "US2/E2E: stage result "
        f"(status={status}, mode={mode}, processed_count={processed_count}, "
        f"push_applied={push_applied}, push_status_code={push_status_code}, "
        f"topic_runs_registered={topic_runs_registered_count}, candidates={discovery_candidate_count})"
    )
    return {
        "status": status,
        "metadata": {
            "mode": mode,
            "scraped_count": scraped_count,
            "new_count": new_count,
            "processed_count": processed_count,
            "discovery_candidate_count": discovery_candidate_count,
            "push_applied": push_applied,
            "push_status_code": push_status_code,
            "push_message": push_message,
            "topic_runs_registered_count": topic_runs_registered_count,
            "topic_runs_registration": topic_runs_registration,
        },
    }


def run_e2e_stage_single_full_rescrape(
    *,
    sample_limit: int,
    sync_runner: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    trace("US2/E2E: running single full-rescrape mode (no incremental pre-pass)")
    result = sync_runner(full_rescrape=True, limit=sample_limit)
    processed_count = int(result.get("processed_count", result.get("new_count", 0)))
    push_applied = bool(result.get("push_applied", False))
    push_status_code = result.get("push_status_code")
    push_message = str(result.get("push_message", ""))
    topic_runs_registered_count = int(result.get("topic_runs_registered_count", 0))
    topic_runs_registration = result.get("topic_runs_registration", [])
    status = "passed" if processed_count >= 1 and push_applied else "failed"
    trace(
        "US2/E2E: stage result "
        f"(status={status}, mode=single_full_rescrape, processed_count={processed_count}, "
        f"push_applied={push_applied}, push_status_code={push_status_code}, "
        f"topic_runs_registered={topic_runs_registered_count}, "
        f"candidates={int(result.get('discovery_candidate_count', 0))})"
    )
    return {
        "status": status,
        "metadata": {
            "mode": "single_full_rescrape",
            "scraped_count": int(result.get("scraped_count", 0)),
            "new_count": int(result.get("new_count", 0)),
            "processed_count": processed_count,
            "discovery_candidate_count": int(result.get("discovery_candidate_count", 0)),
            "push_applied": push_applied,
            "push_status_code": push_status_code,
            "push_message": push_message,
            "topic_runs_registered_count": topic_runs_registered_count,
            "topic_runs_registration": topic_runs_registration,
        },
    }


def run_sql_stage(
    *,
    db_path: Path,
    topic_candidates_emitted: int,
    expected_minimums: dict[str, int],
) -> dict[str, Any]:
    trace(f"US2/SQL: verifying required tables in {db_path}")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if not db_path.exists():
        trace(f"US2/SQL: DB file not found, creating empty file at {db_path}")
        db_path.touch()
    require_topic_candidates = topic_candidates_emitted > 0
    try:
        verifications = verify_sql_tables(
            str(db_path),
            expected_minimums,
            require_topic_candidates=require_topic_candidates,
        )
    except sqlite3.OperationalError as exc:
        detail = str(exc)
        trace(f"US2/SQL: verification failed with sqlite error: {detail}")
        return {
            "status": "failed",
            "metadata": {
                "db_path": str(db_path),
                "require_topic_candidates": require_topic_candidates,
                "required_failures": list(expected_minimums.keys()),
                "tables": {},
                "error_detail": detail,
            },
        }
    verification_rows = {name: asdict(item) for name, item in verifications.items()}
    required_failures = [
        name
        for name, item in verifications.items()
        if item.required_for_pass and item.status != "passed"
    ]
    for table_name, item in verifications.items():
        trace(
            f"US2/SQL: table={table_name} observed={item.observed_updates} "
            f"expected_min={item.expected_min_updates} required={item.required_for_pass} status={item.status}"
        )
    if required_failures:
        trace(f"US2/SQL: required table failures detected: {', '.join(required_failures)}")
    else:
        trace("US2/SQL: all required table checks passed")
    return {
        "status": "failed" if required_failures else "passed",
        "metadata": {
            "db_path": str(db_path),
            "require_topic_candidates": require_topic_candidates,
            "required_failures": required_failures,
            "tables": verification_rows,
        },
    }


def map_embedding_failure_detail(raw_detail: str, fallback_path: str | None) -> str:
    if raw_detail:
        return raw_detail
    if fallback_path:
        return f"Embedding validation failed. Fallback path was provided but unusable: {fallback_path}"
    return "Embedding validation failed: both trusted online access and local fallback are unavailable."


def run_embedding_stage(
    *,
    online_available: bool,
    fallback_path: str | None,
) -> dict[str, Any]:
    trace(
        "US3/Embedding: validating online-or-fallback reliability "
        f"(online_available={online_available}, fallback_path={fallback_path or '<none>'})"
    )
    result = validate_embedding_reliability(
        online_available=online_available,
        local_fallback_path=fallback_path,
    )
    failure_detail = ""
    if result.status != "passed":
        failure_detail = map_embedding_failure_detail(result.error_detail, fallback_path)
        trace(f"US3/Embedding: failed - {failure_detail}")
        trace(
            "US3/Embedding: hint - set LOCAL_EMBEDDING_MODEL_PATH or pass "
            "--embedding-fallback-path to a valid local model path in restricted TLS environments."
        )
    else:
        trace("US3/Embedding: passed")

    return {
        "status": result.status,
        "metadata": {
            "online_path_status": result.online_path_status,
            "local_fallback_status": result.local_fallback_status,
            "fallback_path_valid": result.fallback_path_valid,
            "fallback_path": fallback_path,
            "error_detail": failure_detail,
        },
    }


def build_parser(defaults: dict[str, str]) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Phase 6 deployment/readiness validator")
    parser.add_argument("--compose-file", default=str(DEFAULT_COMPOSE_FILE))
    parser.add_argument("--compose-command", default=defaults.get("VALIDATION_COMPOSE_COMMAND", "podman compose"))
    parser.add_argument("--api-url", default=defaults.get("VALIDATION_API_URL", "http://127.0.0.1:8000/health"))
    parser.add_argument("--push-api-base-url", default=defaults.get("CLOUD_API_BASE_URL", ""))
    parser.add_argument("--ui-url", default=defaults.get("VALIDATION_UI_URL", "http://127.0.0.1:8501/_stcore/health"))
    parser.add_argument("--api-token", default=defaults.get("INGEST_API_TOKEN", ""))
    parser.add_argument("--readiness-timeout", type=int, default=int(defaults.get("VALIDATION_READINESS_TIMEOUT_SECONDS", "300")))
    parser.add_argument("--readiness-interval", type=float, default=float(defaults.get("VALIDATION_READINESS_INTERVAL_SECONDS", "2")))
    parser.add_argument("--output", default=defaults.get("VALIDATION_RUN_OUTPUT_PATH", str(DEFAULT_OUTPUT_PATH)))
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--include-us2", action="store_true")
    parser.add_argument("--include-us3", action="store_true")
    parser.add_argument("--e2e-sample-limit", type=int, default=int(defaults.get("VALIDATION_E2E_SAMPLE_LIMIT", "25")))
    parser.add_argument("--disable-e2e-full-rescrape-fallback", action="store_true")
    parser.add_argument("--test-force-full-rescrape", action="store_true")
    parser.add_argument(
        "--test-e2e-sample-limit",
        type=int,
        default=None,
        help="Override US2 sample size for test runs only (does not change normal env defaults).",
    )
    parser.add_argument("--sql-db-path", default=defaults.get("CLOUD_DB_PATH", ".state/library.db"))
    parser.add_argument("--sql-min-posts", type=int, default=int(defaults.get("VALIDATION_SQL_MIN_POSTS", "1")))
    parser.add_argument("--sql-min-post-topics", type=int, default=int(defaults.get("VALIDATION_SQL_MIN_POST_TOPICS", "1")))
    parser.add_argument("--sql-min-topic-runs", type=int, default=int(defaults.get("VALIDATION_SQL_MIN_TOPIC_RUNS", "1")))
    parser.add_argument("--sql-min-topic-candidates", type=int, default=int(defaults.get("VALIDATION_SQL_MIN_TOPIC_CANDIDATES", "1")))
    parser.add_argument(
        "--embedding-online-available",
        default=defaults.get("VALIDATION_EMBEDDING_ONLINE_AVAILABLE", "false"),
    )
    parser.add_argument(
        "--embedding-fallback-path",
        default=defaults.get("LOCAL_EMBEDDING_MODEL_PATH", ""),
    )
    return parser


def run_validation(args: argparse.Namespace) -> dict[str, Any]:
    trace("Starting Phase 6 validation run")
    ui_url_raw = str(getattr(args, "ui_url", "http://127.0.0.1:8501/_stcore/health")).strip()
    if ui_url_raw.rstrip("/") == "http://127.0.0.1:8501":
        trace("US1/Readiness: auto-adjusting UI probe URL to http://127.0.0.1:8501/_stcore/health")
        args.ui_url = "http://127.0.0.1:8501/_stcore/health"
    run_id = args.run_id or f"phase6-{uuid.uuid4()}"
    started_at = datetime.now(timezone.utc).isoformat()
    project_root = Path.cwd()
    compose_file = Path(args.compose_file)
    output_path = Path(args.output)

    writer = ValidationEvidenceWriter(output_path)

    trace("US1/Deployment: building and starting API/UI containers")
    deployment_stage = run_deployment_stage(
        compose_file=compose_file,
        project_root=project_root,
        compose_command=args.compose_command,
    )
    writer.append_record(
        run_id=run_id,
        check_type="deployment",
        status=deployment_stage["status"],
        payload=deployment_stage["metadata"],
    )
    trace(f"US1/Deployment: status={deployment_stage['status']}")

    if deployment_stage["status"] != "passed":
        trace("US1/Readiness: skipped because deployment failed")
        readiness_stage = {
            "status": "failed",
            "metadata": {
                "skipped": True,
                "reason": "Deployment stage failed; readiness probes were not executed.",
            },
        }
    else:
        trace("US1/Readiness: probing API/UI endpoints")
        readiness_stage = run_readiness_stage(
            api_url=args.api_url,
            ui_url=args.ui_url,
            api_token=(str(getattr(args, "api_token", "")).strip() or None),
            timeout_seconds=args.readiness_timeout,
            interval_seconds=args.readiness_interval,
        )
        trace(f"US1/Readiness: status={readiness_stage['status']}")
    writer.append_record(
        run_id=run_id,
        check_type="readiness",
        status=readiness_stage["status"],
        payload=readiness_stage["metadata"],
    )

    stage_statuses: dict[str, str] = {
        "deployment": deployment_stage["status"],
        "readiness": readiness_stage["status"],
    }
    required_stages = list(US1_REQUIRED_STAGES)

    include_us2 = bool(getattr(args, "include_us2", False))
    push_api_base_url = str(getattr(args, "push_api_base_url", "")).strip()
    previous_phase6_push_api = os.getenv("PHASE6_PUSH_API_BASE_URL")
    if push_api_base_url and not _is_placeholder_base_url(push_api_base_url):
        os.environ["PHASE6_PUSH_API_BASE_URL"] = push_api_base_url
    us1_passed = stage_statuses["deployment"] == "passed" and stage_statuses["readiness"] == "passed"
    try:
        if include_us2:
            if not us1_passed:
                trace("US2 enabled but skipped because US1 (deployment/readiness) did not pass")
                e2e_stage = {
                    "status": "failed",
                    "metadata": {"skipped": True, "reason": "US1 failed, so US2 was not executed."},
                }
                sql_stage = {
                    "status": "failed",
                    "metadata": {"skipped": True, "reason": "US1 failed, so US2 was not executed."},
                }
            else:
                e2e_limit = int(getattr(args, "e2e_sample_limit", 25))
                test_limit = getattr(args, "test_e2e_sample_limit", None)
                if test_limit is not None:
                    e2e_limit = int(test_limit)
                    trace(f"US2/E2E: using test-only sample limit override: {e2e_limit}")
                trace("US2 enabled: running end-to-end and SQL validation")
                if bool(getattr(args, "test_force_full_rescrape", False)):
                    trace("US2/E2E: using test-only single full-rescrape mode")
                    e2e_stage = run_e2e_stage_single_full_rescrape(
                        sample_limit=e2e_limit,
                        sync_runner=run_sync_once,
                    )
                else:
                    e2e_stage = run_e2e_stage(
                        sample_limit=e2e_limit,
                        sync_runner=run_sync_once,
                        allow_full_rescrape_fallback=not bool(getattr(args, "disable_e2e_full_rescrape_fallback", False)),
                    )
                sql_stage = run_sql_stage(
                    db_path=Path(getattr(args, "sql_db_path", ".state/library.db")),
                    topic_candidates_emitted=int(e2e_stage["metadata"].get("discovery_candidate_count", 0)),
                    expected_minimums={
                        "posts": int(getattr(args, "sql_min_posts", 1)),
                        "post_topics": int(getattr(args, "sql_min_post_topics", 1)),
                        "topic_runs": int(getattr(args, "sql_min_topic_runs", 1)),
                        "topic_candidates": int(getattr(args, "sql_min_topic_candidates", 1)),
                    },
                )

            writer.append_record(
                run_id=run_id,
                check_type="e2e",
                status=e2e_stage["status"],
                payload=e2e_stage["metadata"],
            )
            writer.append_record(
                run_id=run_id,
                check_type="sql",
                status=sql_stage["status"],
                payload=sql_stage["metadata"],
            )
            stage_statuses["e2e"] = e2e_stage["status"]
            stage_statuses["sql"] = sql_stage["status"]
            required_stages.extend(list(US2_REQUIRED_STAGES))
    finally:
        if previous_phase6_push_api is None:
            os.environ.pop("PHASE6_PUSH_API_BASE_URL", None)
        else:
            os.environ["PHASE6_PUSH_API_BASE_URL"] = previous_phase6_push_api

    include_us3 = bool(getattr(args, "include_us3", False))
    if include_us3:
        if not us1_passed:
            trace("US3 enabled but skipped because US1 (deployment/readiness) did not pass")
            embedding_stage = {
                "status": "failed",
                "metadata": {"skipped": True, "reason": "US1 failed, so US3 was not executed."},
            }
        else:
            trace("US3 enabled: running embedding reliability validation")
            embedding_stage = run_embedding_stage(
                online_available=parse_bool(str(getattr(args, "embedding_online_available", "false")), False),
                fallback_path=(str(getattr(args, "embedding_fallback_path", "")).strip() or None),
            )
        writer.append_record(
            run_id=run_id,
            check_type="embedding",
            status=embedding_stage["status"],
            payload=embedding_stage["metadata"],
        )
        stage_statuses["embedding"] = embedding_stage["status"]
        required_stages.extend(list(US3_REQUIRED_STAGES))

    overall_status, failed_mandatory = evaluate_mandatory_stage_outcomes(
        stage_statuses,
        required_stages=tuple(required_stages),
    )

    summary = {
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "overall_status": overall_status,
        "failed_mandatory_stages": failed_mandatory,
        "stage_statuses": stage_statuses,
        "output_path": str(output_path),
        "deployment_script_metadata": {
            "compose_file": str(compose_file),
            "compose_command": args.compose_command,
            "script_entrypoint": str(Path(__file__).resolve()),
        },
        "options": {
            "include_us2": include_us2,
            "include_us3": include_us3,
        },
    }

    writer.append_record(
        run_id=run_id,
        check_type="summary",
        status=overall_status,
        payload=summary,
    )
    trace(
        "Validation completed "
        f"(overall_status={overall_status}, failed_mandatory={failed_mandatory}, output={output_path})"
    )
    return summary


def main() -> int:
    root_values = load_env_file(ROOT_ENV_FILE)
    cloud_values = load_env_file(CLOUD_ENV_FILE)
    runtime_defaults = dict(root_values)
    runtime_defaults.update(cloud_values)
    for key, value in runtime_defaults.items():
        os.environ.setdefault(key, value)
    trace(f"Loaded defaults from {ROOT_ENV_FILE} and {CLOUD_ENV_FILE}")
    maybe_warn_windows_data_dir(runtime_defaults)
    args = build_parser(runtime_defaults).parse_args()
    preflight_errors, preflight_warnings = validate_preflight_configuration(args, root_values, cloud_values)
    for warning in preflight_warnings:
        trace(f"Preflight warning: {warning}")
    if preflight_errors:
        trace("Preflight validation failed. Fix the following .env configuration issues:")
        for issue in preflight_errors:
            trace(f"  - {issue}")
        return 2
    resolved_sql_db_path = resolve_sql_db_path_for_host(
        str(getattr(args, "sql_db_path", "")),
        data_dir_raw=str(cloud_values.get("DATA_DIR", "")),
        repo_root=REPO_ROOT,
    )
    if str(resolved_sql_db_path) != str(getattr(args, "sql_db_path", "")):
        trace(
            f"US2/SQL: resolved container DB path '{args.sql_db_path}' "
            f"to host path '{resolved_sql_db_path}'"
        )
    args.sql_db_path = str(resolved_sql_db_path)
    summary = run_validation(args)
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["overall_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
