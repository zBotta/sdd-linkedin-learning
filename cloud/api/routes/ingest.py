from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from cloud.api.auth import require_ingest_token
from cloud.api.schemas import IngestBatchRequest, IngestBatchResponse

router = APIRouter(tags=["ingest"], dependencies=[Depends(require_ingest_token)])


@router.post("/ingest/batch", response_model=IngestBatchResponse)
def ingest_batch(payload: IngestBatchRequest, request: Request) -> IngestBatchResponse:
    service = request.app.state.ingest_service
    result = service.ingest_batch(payload)
    return result
