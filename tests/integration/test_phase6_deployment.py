from __future__ import annotations

from argparse import Namespace
from pathlib import Path
import tempfile

from scripts import validate_phase6


def test_deployment_stage_records_success(monkeypatch) -> None:
    class Result:
        status = "passed"
        command = ["podman-compose", "-f", "cloud/docker-compose.yml", "up", "-d", "--build"]
        exit_code = 0
        stdout = "ok"
        stderr = ""

    monkeypatch.setattr(validate_phase6, "run_podman_deployment", lambda **_: Result())

    temp_root = Path(tempfile.mkdtemp(prefix="phase6-", dir="tests/integration"))
    stage = validate_phase6.run_deployment_stage(
        compose_file=Path("cloud/docker-compose.yml"),
        project_root=temp_root,
        compose_command="podman-compose",
    )

    assert stage["status"] == "passed"
    assert stage["metadata"]["exit_code"] == 0


def test_validate_script_entrypoint_success(monkeypatch) -> None:
    monkeypatch.setattr(
        validate_phase6,
        "run_deployment_stage",
        lambda **_: {
            "status": "passed",
            "metadata": {"command": ["podman-compose"], "exit_code": 0, "stdout": "ok", "stderr": ""},
        },
    )
    monkeypatch.setattr(
        validate_phase6,
        "run_readiness_stage",
        lambda **_: {
            "status": "passed",
            "metadata": {"services": {"api": {"status": "passed"}, "ui": {"status": "passed"}}},
        },
    )

    output_path = Path("tests/integration/phase6_evidence_test.jsonl")
    if output_path.exists():
        output_path.unlink()

    args = Namespace(
        compose_file="cloud/docker-compose.yml",
        compose_command="podman-compose",
        api_url="http://127.0.0.1:8000/health",
        ui_url="http://127.0.0.1:8501/",
        readiness_timeout=300,
        readiness_interval=0.01,
        output=str(output_path),
        run_id="us1-success",
    )

    summary = validate_phase6.run_validation(args)

    assert summary["overall_status"] == "passed"
    assert summary["stage_statuses"]["deployment"] == "passed"
    assert summary["stage_statuses"]["readiness"] == "passed"
    assert output_path.exists()


def test_readiness_is_not_probed_when_deployment_fails(monkeypatch) -> None:
    monkeypatch.setattr(
        validate_phase6,
        "run_deployment_stage",
        lambda **_: {
            "status": "failed",
            "metadata": {"command": ["podman", "compose"], "exit_code": 127, "stdout": "", "stderr": "not found"},
        },
    )

    called = {"value": False}

    def _unexpected_readiness(**_):
        called["value"] = True
        return {"status": "passed", "metadata": {}}

    monkeypatch.setattr(validate_phase6, "run_readiness_stage", _unexpected_readiness)

    output_path = Path("tests/integration/phase6_evidence_test.jsonl")
    if output_path.exists():
        output_path.unlink()

    args = Namespace(
        compose_file="cloud/docker-compose.yml",
        compose_command="podman compose",
        api_url="http://127.0.0.1:8000/health",
        ui_url="http://127.0.0.1:8501/",
        readiness_timeout=300,
        readiness_interval=0.01,
        output=str(output_path),
        run_id="us1-fail-fast",
    )

    summary = validate_phase6.run_validation(args)

    assert called["value"] is False
    assert summary["overall_status"] == "failed"
    assert summary["stage_statuses"]["deployment"] == "failed"
    assert summary["stage_statuses"]["readiness"] == "failed"


def test_resolve_sql_db_path_maps_container_data_path_to_host_data_dir() -> None:
    resolved = validate_phase6.resolve_sql_db_path_for_host(
        "/data/library.db",
        data_dir_raw="./.state/cloud-data",
        repo_root=Path.cwd(),
    )
    expected = (Path.cwd() / "cloud" / ".state" / "cloud-data" / "library.db").resolve()
    assert resolved.resolve() == expected
