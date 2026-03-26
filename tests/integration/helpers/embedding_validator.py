from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class EmbeddingValidationResult:
    online_path_status: str
    local_fallback_status: str
    fallback_path_valid: bool
    error_detail: str
    status: str


def validate_embedding_reliability(
    *,
    online_available: bool,
    local_fallback_path: str | None,
) -> EmbeddingValidationResult:
    fallback_valid = bool(local_fallback_path) and Path(str(local_fallback_path)).exists()
    online_status = "passed" if online_available else "failed"
    fallback_status = "passed" if fallback_valid else "failed"

    if online_available or fallback_valid:
        return EmbeddingValidationResult(
            online_path_status=online_status,
            local_fallback_status=fallback_status,
            fallback_path_valid=fallback_valid,
            error_detail="",
            status="passed",
        )

    if local_fallback_path:
        detail = f"Configured local fallback path is invalid or unreadable: {local_fallback_path}"
    else:
        detail = "No local embedding fallback path is configured and online embedding is unavailable."

    return EmbeddingValidationResult(
        online_path_status=online_status,
        local_fallback_status=fallback_status,
        fallback_path_valid=fallback_valid,
        error_detail=detail,
        status="failed",
    )
