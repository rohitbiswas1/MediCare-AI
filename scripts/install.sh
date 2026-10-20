#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
umask 077
mkdir -p .local/cache
export UV_CACHE_DIR="${MEDICARE_CACHE_DIR:-$repo_root/.local/cache}/uv"
export npm_config_cache="${MEDICARE_CACHE_DIR:-$repo_root/.local/cache}/npm"
export npm_config_update_notifier=false
command -v node >/dev/null
command -v uv >/dev/null
command -v docker >/dev/null
command -v tesseract >/dev/null || { echo 'Install Tesseract OCR 5 with English language data before continuing.' >&2; exit 1; }
node -e 'if(Number(process.versions.node.split(".")[0])<22)process.exit(1)'
npm ci --no-fund --no-audit
uv sync --frozen --project services/api
if [[ "${1:-}" == '--ml' ]]; then uv sync --frozen --project ml; fi
docker compose up -d --wait postgres redis
(cd services/api && uv run --frozen alembic upgrade head)
echo 'Dependencies installed; PostgreSQL and Redis healthy; migrations applied.'
