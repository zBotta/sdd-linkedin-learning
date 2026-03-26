from __future__ import annotations

from urllib.error import URLError

from tests.integration.helpers.readiness_probe import probe_required_services


def test_readiness_probe_fails_within_timeout_window() -> None:
    attempts = {"count": 0}

    def fake_urlopen(req, timeout=5):
        _ = req
        _ = timeout
        attempts["count"] += 1
        raise URLError("connection refused")

    class Clock:
        def __init__(self) -> None:
            self.current = 0.0

        def now(self) -> float:
            return self.current

        def sleep(self, seconds: float) -> None:
            self.current += seconds

    clock = Clock()

    import tests.integration.helpers.readiness_probe as readiness_probe

    original = readiness_probe.request.urlopen
    readiness_probe.request.urlopen = fake_urlopen
    try:
        results = probe_required_services(
            {"api": "http://127.0.0.1:8000/health"},
            timeout_seconds=300,
            probe_interval_seconds=120,
            now_fn=clock.now,
            sleep_fn=clock.sleep,
        )
    finally:
        readiness_probe.request.urlopen = original

    api_result = results["api"]
    assert api_result.status == "failed"
    assert api_result.max_window_seconds == 300
    assert attempts["count"] >= 3
