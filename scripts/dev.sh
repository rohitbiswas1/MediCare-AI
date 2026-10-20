#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
umask 077
runtime_dir="$repo_root/.local/run"
mkdir -p "$runtime_dir"
docker compose up -d --wait postgres redis
(cd services/api && .venv/bin/alembic upgrade head)
start_process() {
  local label="$1" directory="$2"
  shift 2
  if [[ -f "$runtime_dir/$label.pid" ]]; then
    local saved_pid saved_identity saved_state current_identity
    saved_pid="$(cat "$runtime_dir/$label.pid")"
    saved_identity="$(cat "$runtime_dir/$label.started" 2>/dev/null || true)"
    current_identity="$(cat /proc/sys/kernel/random/boot_id; ps -o lstart= -p "$saved_pid" 2>/dev/null || true)"
    saved_state="$(ps -o stat= -p "$saved_pid" 2>/dev/null || true)"
    if [[ -n "$saved_state" && "$saved_state" != *Z* && "$saved_identity" == "$current_identity" ]]; then return; fi
  fi
  (cd "$directory"; nohup setsid "$@" > "$runtime_dir/$label.log" 2>&1 < /dev/null &
   process_id=$!
   echo "$process_id" > "$runtime_dir/$label.pid"
   { cat /proc/sys/kernel/random/boot_id; ps -o lstart= -p "$process_id"; } > "$runtime_dir/$label.started")
}
if ! curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; then
 start_process api "$repo_root/services/api" .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log
fi
# Worker and beat have their own PID files; only one scheduler should run per environment.
start_process worker "$repo_root/services/api" .venv/bin/celery -A app.jobs:celery worker --loglevel=WARNING --concurrency=2
start_process beat "$repo_root/services/api" .venv/bin/celery -A app.jobs:celery beat --loglevel=WARNING --schedule "$runtime_dir/beat-schedule" --pidfile ""
if ! curl -fsS http://127.0.0.1:3000/api/v1/health >/dev/null 2>&1; then
 if [[ "${MEDICARE_WEB_MODE:-development}" == 'production' ]]; then
   [[ -f "$repo_root/apps/web/.next/BUILD_ID" ]] || { echo 'Run npm run build first.' >&2; exit 1; }
   start_process web "$repo_root/apps/web" node "$repo_root/node_modules/next/dist/bin/next" start --hostname 0.0.0.0
 else
   start_process web "$repo_root/apps/web" node "$repo_root/node_modules/next/dist/bin/next" dev --webpack --hostname 0.0.0.0
 fi
fi
for ((attempt=0; attempt<40; attempt++)); do
 if curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1 && curl -fsS http://127.0.0.1:3000/api/v1/health >/dev/null 2>&1; then
   echo 'API and frontend proxy are healthy. Logs and PID files: .local/run/'
   exit 0
 fi
 sleep 1
done
echo 'Startup failed. Inspect .local/run/*.log.' >&2
exit 1
