#!/usr/bin/env bash
set -euo pipefail

APP_USER="${APP_USER:-ec2-user}"
APP_GROUP="${APP_GROUP:-ec2-user}"
APP_DIR="${APP_DIR:-/opt/linkedin-library}"
CLOUD_DIR="${CLOUD_DIR:-${APP_DIR}/cloud}"
DATA_DIR="${DATA_DIR:-/srv/linkedin-library/data}"
BACKUP_DIR="${BACKUP_DIR:-/srv/linkedin-library/backups}"
LOG_DIR="${LOG_DIR:-/var/log/linkedin-library}"
DATA_DEVICE="${DATA_DEVICE:-/dev/nvme1n1}"
AWS_REGION="${AWS_REGION:-$(curl -s http://169.254.169.254/latest/meta-data/placement/region || echo us-east-1)}"
REPO_URL="${REPO_URL:-}"
REPO_REF="${REPO_REF:-main}"

# Parameter names can be overridden as space-delimited strings.
SSM_PARAMS_SECURE="${SSM_PARAMS_SECURE:-/linkedin-library/prod/INGEST_API_TOKEN /linkedin-library/prod/UI_ACCESS_PASSWORD}"
SSM_PARAMS_PLAIN="${SSM_PARAMS_PLAIN:-/linkedin-library/prod/API_PORT /linkedin-library/prod/UI_PORT}"

log() {
  echo "[$(date -Is)] $*"
}

install_packages() {
  if command -v dnf >/dev/null 2>&1; then
    dnf update -y
    dnf install -y docker awscli jq git rsync
    dnf install -y docker-compose-plugin || true
  elif command -v yum >/dev/null 2>&1; then
    yum update -y
    yum install -y docker awscli jq git rsync
  elif command -v apt-get >/dev/null 2>&1; then
    apt-get update
    apt-get install -y docker.io awscli jq git rsync
  else
    log "Unsupported OS package manager"
    exit 1
  fi
}

ensure_docker() {
  systemctl enable docker
  systemctl start docker
  usermod -aG docker "${APP_USER}" || true
}

prepare_storage() {
  mkdir -p "${DATA_DIR}" "${BACKUP_DIR}" "${LOG_DIR}"

  if [ -b "${DATA_DEVICE}" ]; then
    if ! blkid "${DATA_DEVICE}" >/dev/null 2>&1; then
      log "Formatting ${DATA_DEVICE} as ext4"
      mkfs.ext4 -F "${DATA_DEVICE}"
    fi

    mkdir -p /mnt/linkedin-library-ebs
    mountpoint -q /mnt/linkedin-library-ebs || mount "${DATA_DEVICE}" /mnt/linkedin-library-ebs
    grep -q "${DATA_DEVICE}" /etc/fstab || echo "${DATA_DEVICE} /mnt/linkedin-library-ebs ext4 defaults,nofail 0 2" >> /etc/fstab

    mkdir -p /mnt/linkedin-library-ebs/data /mnt/linkedin-library-ebs/backups
    rsync -a --ignore-existing "${DATA_DIR}/" /mnt/linkedin-library-ebs/data/ || true
    rsync -a --ignore-existing "${BACKUP_DIR}/" /mnt/linkedin-library-ebs/backups/ || true

    rm -rf "${DATA_DIR}" "${BACKUP_DIR}"
    ln -s /mnt/linkedin-library-ebs/data "${DATA_DIR}"
    ln -s /mnt/linkedin-library-ebs/backups "${BACKUP_DIR}"
  fi

  chown -R "${APP_USER}:${APP_GROUP}" "${APP_DIR}" "${LOG_DIR}" "${DATA_DIR}" "${BACKUP_DIR}" || true
}

checkout_repo() {
  mkdir -p "${APP_DIR}"
  if [ -n "${REPO_URL}" ]; then
    if [ ! -d "${APP_DIR}/.git" ]; then
      git clone "${REPO_URL}" "${APP_DIR}"
    fi
    git -C "${APP_DIR}" fetch --all --tags
    git -C "${APP_DIR}" checkout "${REPO_REF}"
    git -C "${APP_DIR}" pull --ff-only
  fi
}

ssm_get_plain() {
  local name="$1"
  aws ssm get-parameter --name "${name}" --region "${AWS_REGION}" --query 'Parameter.Value' --output text
}

ssm_get_secure() {
  local name="$1"
  aws ssm get-parameter --name "${name}" --with-decryption --region "${AWS_REGION}" --query 'Parameter.Value' --output text
}

write_env_file() {
  mkdir -p "${CLOUD_DIR}"
  local env_file="${CLOUD_DIR}/.env"

  local ingest_token
  ingest_token="$(ssm_get_secure "$(echo "${SSM_PARAMS_SECURE}" | awk '{print $1}')")"
  local ui_password
  ui_password="$(ssm_get_secure "$(echo "${SSM_PARAMS_SECURE}" | awk '{print $2}')")"

  local api_port ui_port
  api_port="$(ssm_get_plain "$(echo "${SSM_PARAMS_PLAIN}" | awk '{print $1}')" 2>/dev/null || echo 8000)"
  ui_port="$(ssm_get_plain "$(echo "${SSM_PARAMS_PLAIN}" | awk '{print $2}')" 2>/dev/null || echo 8501)"

  cat > "${env_file}" <<EOF
INGEST_API_TOKEN=${ingest_token}
UI_ACCESS_PASSWORD=${ui_password}
CLOUD_DB_PATH=/data/library.db
API_PORT=${api_port}
UI_PORT=${ui_port}
DATA_DIR=${DATA_DIR}
EOF

  chmod 600 "${env_file}"
  chown "${APP_USER}:${APP_GROUP}" "${env_file}" || true
}

start_stack() {
  if [ ! -f "${CLOUD_DIR}/docker-compose.yml" ]; then
    log "Missing docker-compose.yml in ${CLOUD_DIR}"
    exit 1
  fi

  cd "${CLOUD_DIR}"
  docker compose pull || true
  docker compose up -d --build
}

main() {
  log "Installing dependencies"
  install_packages
  ensure_docker

  log "Preparing persistent storage"
  prepare_storage

  log "Ensuring repository checkout"
  checkout_repo

  log "Writing runtime environment from Parameter Store"
  write_env_file

  log "Starting docker compose stack"
  start_stack

  log "Bootstrap complete"
}

main "$@"
