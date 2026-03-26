from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import time
from urllib import request
from urllib.error import URLError

import pytest

from local_sync.push_client import PushClient

pytestmark = pytest.mark.real_runtime


def _load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _run_compose(
    args: list[str],
    *,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    command = ["podman", "compose", "-f", "cloud/docker-compose.yml", *args]
    return subprocess.run(
        command,
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        check=check,
        env=env,
    )


def _compose_available() -> bool:
    try:
        completed = subprocess.run(
            ["podman", "compose", "version"],
            capture_output=True,
            text=True,
            check=False,
        )
        return completed.returncode == 0
    except FileNotFoundError:
        return False


def _wait_http_ok(url: str, *, timeout_seconds: int, headers: dict[str, str] | None = None) -> None:
    started = time.monotonic()
    while time.monotonic() - started <= timeout_seconds:
        req = request.Request(url, method="GET", headers=headers or {})
        try:
            with request.urlopen(req, timeout=5) as response:
                code = getattr(response, "status", response.getcode())
                if 200 <= code < 300:
                    return
        except URLError:
            pass
        time.sleep(2)
    raise AssertionError(f"Endpoint did not become healthy in {timeout_seconds}s: {url}")


@pytest.fixture(scope="module")
def running_phase6_stack() -> dict[str, str]:
    if os.getenv("RUN_REAL_DEPLOY_TESTS", "0") != "1":
        pytest.skip("Set RUN_REAL_DEPLOY_TESTS=1 to execute real podman deployment tests.")

    if not _compose_available():
        pytest.skip("podman compose is not available/connected on this machine.")

    local_data_dir = (Path.cwd() / ".state" / "cloud-data-realtest").resolve()
    local_data_dir.mkdir(parents=True, exist_ok=True)
    compose_env = dict(os.environ)
    compose_env["DATA_DIR"] = str(local_data_dir)

    _run_compose(["down", "--remove-orphans"], check=False, env=compose_env)
    up = _run_compose(["up", "-d", "--build"], check=False, env=compose_env)
    assert up.returncode == 0, f"podman compose up --build failed\nSTDOUT:\n{up.stdout}\nSTDERR:\n{up.stderr}"

    env_values = _load_env_file(Path("cloud/.env"))
    token = env_values.get("INGEST_API_TOKEN", "")
    assert token, "INGEST_API_TOKEN must be set in cloud/.env for health/push checks."

    try:
        _wait_http_ok(
            "http://127.0.0.1:8000/health",
            timeout_seconds=300,
            headers={"Authorization": f"Bearer {token}"},
        )
        _wait_http_ok("http://127.0.0.1:8501/_stcore/health", timeout_seconds=300)
        yield {"token": token}
    finally:
        _run_compose(["down", "--remove-orphans"], check=False, env=compose_env)


def test_real_deployment_build_and_health(running_phase6_stack: dict[str, str]) -> None:
    assert running_phase6_stack["token"]


def test_real_local_sync_push_client_to_api(running_phase6_stack: dict[str, str]) -> None:
    token = running_phase6_stack["token"]
    push_client = PushClient(
        base_url="http://127.0.0.1:8000",
        token=token,
        enabled=True,
        timeout_seconds=20,
    )

    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "batchId": "phase6-real-runtime-batch",
        "sentAt": now,
        "source": "local_sync",
        "posts": [
            {
                "source": "linkedin_saved",
                "sourcePostId": "phase6-real-post-1",
                "savedAt": now,
                "content": "Real runtime push client validation post.",
                "contentHash": "phase6-real-hash-1",
                "title": "Phase 6 Real Runtime",
                "metadataJson": {"kind": "runtime-test"},
                "status": "new",
            }
        ],
        "topics": [],
        "postTopics": [],
        "topicCandidates": [],
        "notes": [],
    }

    result = push_client.push_payload(payload)
    assert result.applied is True, result.message
