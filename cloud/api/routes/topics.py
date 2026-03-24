from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from cloud.api.auth import require_ingest_token
from cloud.api.schemas import TopicCandidateDecision, TopicCandidateResponse, TopicRunCreate

router = APIRouter(tags=["topics"], dependencies=[Depends(require_ingest_token)])


@router.post("/topic-runs")
def create_topic_run(payload: TopicRunCreate, request: Request) -> dict[str, object]:
    service = request.app.state.ingest_service
    return service.create_topic_run(payload)


@router.get("/topic-candidates", response_model=list[TopicCandidateResponse])
def get_topic_candidates(request: Request, state: str | None = Query(default=None)) -> list[TopicCandidateResponse]:
    service = request.app.state.ingest_service
    return service.list_topic_candidates(state=state)


@router.post("/topic-candidates/{candidate_id}/decision", response_model=TopicCandidateResponse)
def decide_topic_candidate(
    candidate_id: str,
    payload: TopicCandidateDecision,
    request: Request,
) -> TopicCandidateResponse:
    service = request.app.state.ingest_service
    result = service.apply_candidate_decision(candidate_id, payload)
    if result is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return result
