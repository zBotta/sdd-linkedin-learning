from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Callable
from urllib import request
from urllib.error import URLError


@dataclass(slots=True)
class ReadinessCheckResult:
    service_name: str
    probe: str
    attempts: int
    max_window_seconds: int
    status: str
    last_observed_detail: str


def probe_required_services(
    service_probes: dict[str, str],
    *,
    timeout_seconds: int = 300,
    probe_interval_seconds: float = 2.0,
    request_timeout_seconds: float = 5.0,
    request_headers_by_service: dict[str, dict[str, str]] | None = None,
    now_fn: Callable[[], float] | None = None,
    sleep_fn: Callable[[float], None] | None = None,
) -> dict[str, ReadinessCheckResult]:
    now = now_fn or time.monotonic
    sleep = sleep_fn or time.sleep
    results: dict[str, ReadinessCheckResult] = {}

    for service_name, probe_url in service_probes.items():
        deadline = now() + timeout_seconds
        attempts = 0
        last_detail = "No probe attempts made"
        status = "failed"
        headers = (request_headers_by_service or {}).get(service_name, {})

        while now() <= deadline:
            attempts += 1
            req = request.Request(probe_url, method="GET", headers=headers)
            try:
                with request.urlopen(req, timeout=request_timeout_seconds) as response:
                    code = getattr(response, "status", response.getcode())
                    if 200 <= code < 300:
                        status = "passed"
                        last_detail = f"HTTP {code}"
                        break
                    last_detail = f"HTTP {code}"
            except URLError as exc:
                reason = getattr(exc, "reason", str(exc))
                last_detail = f"Probe error: {reason}"
            except Exception as exc:  # pragma: no cover - defensive catch-all
                last_detail = f"Probe exception: {exc}"

            if now() > deadline:
                break
            sleep(probe_interval_seconds)

        results[service_name] = ReadinessCheckResult(
            service_name=service_name,
            probe=probe_url,
            attempts=attempts,
            max_window_seconds=timeout_seconds,
            status=status,
            last_observed_detail=last_detail,
        )

    return results
