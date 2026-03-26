from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shlex
import subprocess


@dataclass(slots=True)
class DeploymentStageResult:
    command: list[str]
    exit_code: int
    status: str
    stdout: str
    stderr: str


def _split_command(command: str) -> list[str]:
    value = (command or "").strip()
    if not value:
        return ["podman", "compose"]
    return shlex.split(value, posix=False)


def _load_env_value(env_file: Path, key: str) -> str | None:
    if not env_file.exists():
        return None
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() != key:
            continue
        # Strip inline comments to avoid accidental path corruption in runtime.
        return v.split("#", 1)[0].strip()
    return None


def _ensure_data_dir_exists(env_file: Path) -> None:
    data_dir = _load_env_value(env_file, "DATA_DIR")
    if not data_dir:
        return
    path = Path(data_dir)
    if not path.is_absolute():
        path = (env_file.parent / path).resolve()
    path.mkdir(parents=True, exist_ok=True)


def run_podman_deployment(
    compose_file: Path,
    project_directory: Path,
    compose_command: str = "podman compose",
) -> DeploymentStageResult:
    env_file = compose_file.parent / ".env"
    _ensure_data_dir_exists(env_file)
    command = _split_command(compose_command) + ["-f", str(compose_file)]
    if env_file.exists():
        command.extend(["--env-file", str(env_file)])
    command.extend(["up", "-d", "--build"])

    try:
        completed = subprocess.run(
            command,
            cwd=project_directory,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        status = "passed" if completed.returncode == 0 else "failed"
        return DeploymentStageResult(
            command=command,
            exit_code=completed.returncode,
            status=status,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
    except FileNotFoundError as exc:
        return DeploymentStageResult(
            command=command,
            exit_code=127,
            status="failed",
            stdout="",
            stderr=(
                "Deployment command not found. Install Podman with compose support, "
                "or set VALIDATION_COMPOSE_COMMAND (for example: 'podman compose'). "
                f"Details: {exc}"
            ),
        )
