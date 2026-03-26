#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/cloud/docker-compose.yml"
ENV_FILE="${REPO_ROOT}/cloud/.env"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/deploy_cloud_ec2.sh [command] [service]

Commands:
  up        Build and start API/UI containers in background (default)
  down      Stop and remove containers/network
  restart   Recreate containers with latest image/build context
  ps        Show compose service status
  logs      Tail logs (all services, or pass a service name)

Examples:
  ./scripts/deploy_cloud_ec2.sh up
  ./scripts/deploy_cloud_ec2.sh logs api
  ./scripts/deploy_cloud_ec2.sh restart
EOF
}

require_bin() {
  local bin_name="$1"
  if ! command -v "${bin_name}" >/dev/null 2>&1; then
    echo "[ec2-deploy] Missing required command: ${bin_name}" >&2
    exit 1
  fi
}

require_file() {
  local file_path="$1"
  if [[ ! -f "${file_path}" ]]; then
    echo "[ec2-deploy] Missing required file: ${file_path}" >&2
    exit 1
  fi
}

resolve_data_dir() {
  local raw
  raw="$(grep -E '^DATA_DIR=' "${ENV_FILE}" | tail -n 1 | cut -d'=' -f2- | tr -d '\r' | xargs || true)"
  if [[ -z "${raw}" ]]; then
    echo "[ec2-deploy] cloud/.env -> DATA_DIR is empty. Set DATA_DIR to a writable path (example: /srv/linkedin-library/data)." >&2
    exit 1
  fi

  if [[ "${raw}" = /* ]]; then
    printf '%s\n' "${raw}"
    return
  fi

  printf '%s\n' "${REPO_ROOT}/cloud/${raw}"
}

run_compose() {
  podman compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" "$@"
}

main() {
  local command="${1:-up}"
  local service="${2:-}"

  require_bin podman
  require_file "${COMPOSE_FILE}"
  require_file "${ENV_FILE}"

  if ! podman compose version >/dev/null 2>&1; then
    echo "[ec2-deploy] 'podman compose' is not available. Install/enable Podman Compose provider first." >&2
    exit 1
  fi

  local data_dir
  data_dir="$(resolve_data_dir)"
  mkdir -p "${data_dir}"

  cd "${REPO_ROOT}"
  echo "[ec2-deploy] Repo root: ${REPO_ROOT}"
  echo "[ec2-deploy] Using compose file: ${COMPOSE_FILE}"
  echo "[ec2-deploy] Using env file: ${ENV_FILE}"
  echo "[ec2-deploy] Ensured DATA_DIR exists: ${data_dir}"

  case "${command}" in
    up)
      echo "[ec2-deploy] Building and starting API/UI containers..."
      run_compose up -d --build
      run_compose ps
      ;;
    down)
      echo "[ec2-deploy] Stopping and removing containers..."
      run_compose down --remove-orphans
      ;;
    restart)
      echo "[ec2-deploy] Restarting API/UI containers..."
      run_compose down --remove-orphans
      run_compose up -d --build
      run_compose ps
      ;;
    ps)
      run_compose ps
      ;;
    logs)
      if [[ -n "${service}" ]]; then
        run_compose logs -f "${service}"
      else
        run_compose logs -f
      fi
      ;;
    help|-h|--help)
      usage
      ;;
    *)
      echo "[ec2-deploy] Unknown command: ${command}" >&2
      usage
      exit 1
      ;;
  esac
}

main "$@"
