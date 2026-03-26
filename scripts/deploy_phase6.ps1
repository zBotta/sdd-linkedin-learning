$ErrorActionPreference = "Stop"
$env:UV_CACHE_DIR = Join-Path (Get-Location) ".state\\uv-cache"
New-Item -ItemType Directory -Force $env:UV_CACHE_DIR | Out-Null
uv run --no-sync python scripts/validate_phase6.py @Args
