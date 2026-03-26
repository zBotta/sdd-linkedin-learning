#!/usr/bin/env bash
set -euo pipefail

export UV_CACHE_DIR="${UV_CACHE_DIR:-.state/uv-cache}"
mkdir -p "$UV_CACHE_DIR"

uv run --no-sync python scripts/validate_phase6.py "$@"
