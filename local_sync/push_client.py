from __future__ import annotations

import json
from typing import Any
from urllib import error, request

from shared.schemas import IngestBatchRequest, NormalizedPost, PushResult


class PushClient:
    """Authenticated push client with a safe dry-run mode for local prototyping."""

    def __init__(
        self,
        base_url: str,
        token: str,
        enabled: bool,
        timeout_seconds: int = 20,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._enabled = enabled
        self._timeout_seconds = timeout_seconds

    def build_payload(self, posts: list[NormalizedPost]) -> dict[str, Any]:
        batch = IngestBatchRequest(posts=posts)
        return batch.model_dump(mode="json")

    def push_payload(self, payload: dict[str, Any]) -> PushResult:
        if not self._enabled:
            return PushResult(applied=True, dry_run=True, message="Push disabled; payload prepared only")

        if not self._base_url or not self._token:
            return PushResult(
                applied=False,
                dry_run=False,
                status_code=None,
                message="Missing CLOUD_API_BASE_URL or CLOUD_INGEST_TOKEN",
            )

        endpoint = f"{self._base_url}/ingest/batch"
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._token}",
        }

        req = request.Request(endpoint, data=body, headers=headers, method="POST")

        try:
            with request.urlopen(req, timeout=self._timeout_seconds) as response:
                return PushResult(
                    applied=200 <= response.status < 300,
                    dry_run=False,
                    status_code=response.status,
                    message="Payload sent",
                )
        except error.HTTPError as exc:
            return PushResult(applied=False, dry_run=False, status_code=exc.code, message=str(exc))
        except error.URLError as exc:
            return PushResult(applied=False, dry_run=False, status_code=None, message=str(exc))
