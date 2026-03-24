from __future__ import annotations

import logging
import uuid
from time import perf_counter

from starlette.requests import Request

logger = logging.getLogger("cloud.api")


def start_request(request: Request) -> tuple[str, float]:
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    request.state.request_id = request_id
    return request_id, perf_counter()


def end_request(request: Request, started: float, status_code: int) -> None:
    elapsed_ms = int((perf_counter() - started) * 1000)
    logger.info(
        "request_id=%s method=%s path=%s status=%s elapsed_ms=%s",
        getattr(request.state, "request_id", "n/a"),
        request.method,
        request.url.path,
        status_code,
        elapsed_ms,
    )
