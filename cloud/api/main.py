from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Request

from cloud.api.routes.ingest import router as ingest_router
from cloud.api.routes.system import router as system_router
from cloud.api.routes.topics import router as topics_router
from cloud.api.services.ingest_service import IngestService
from cloud.api.services.telemetry import end_request, start_request
from shared.db import Database


def create_app() -> FastAPI:
    app = FastAPI(title="LinkedIn Saved Library Ingest API", version="1.0.0")

    db_path = Path(os.getenv("CLOUD_DB_PATH", ".state/library.db"))
    db = Database(db_path)
    db.initialize()

    app.state.db = db
    app.state.ingest_service = IngestService(db)

    @app.middleware("http")
    async def telemetry_middleware(request: Request, call_next):
        request_id, started = start_request(request)
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        end_request(request, started, response.status_code)
        return response

    app.include_router(system_router)
    app.include_router(ingest_router)
    app.include_router(topics_router)
    return app


app = create_app()
