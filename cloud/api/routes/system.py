from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request

from cloud.api.auth import require_ingest_token
from cloud.api.schemas import HealthResponse, SyncStatusResponse

router = APIRouter(tags=["system"], dependencies=[Depends(require_ingest_token)])


@router.get("/health", response_model=HealthResponse)
def get_health(request: Request) -> HealthResponse:
    service = request.app.state.ingest_service
    data = service.health()
    return HealthResponse(
        status=data["status"],
        db=data["db"],
        timestamp=datetime.fromisoformat(data["timestamp"]),
    )


@router.get("/sync-status", response_model=SyncStatusResponse)
def get_sync_status(request: Request) -> SyncStatusResponse:
    service = request.app.state.ingest_service
    data = service.sync_status()
    return SyncStatusResponse.model_validate(data)
