from __future__ import annotations

import os

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer = HTTPBearer(auto_error=False)


def _expected_token() -> str:
    return os.getenv("INGEST_API_TOKEN", "dev-ingest-token")


def require_ingest_token(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> None:
    if creds is None or creds.scheme.lower() != "bearer" or creds.credentials != _expected_token():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
