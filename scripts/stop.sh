#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
for label in web api worker beat; do
 file="$repo_root/.local/run/$label.pid"
 if [[ -f "$file" ]]; then
  process_id="$(cat "$file")"
  if [[ "$process_id" =~ ^[0-9]+$ ]]; then
   # Match boot identity and start time even when a server changes its process title.
   saved_identity="$(cat "$repo_root/.local/run/$label.started" 2>/dev/null || true)"
   current_identity="$(cat /proc/sys/kernel/random/boot_id; ps -o lstart= -p "$process_id" 2>/dev/null || true)"
   if [[ -n "$saved_identity" && "$saved_identity" == "$current_identity" ]]; then
     process_group="$(ps -o pgid= -p "$process_id" | tr -d ' ')"
     if [[ "$process_group" == "$process_id" ]]; then kill -TERM -- "-$process_id" 2>/dev/null || true;
     else kill -TERM "$process_id" 2>/dev/null || true; fi
     for ((attempt=0; attempt<50; attempt++)); do
       process_state="$(ps -o stat= -p "$process_id" 2>/dev/null || true)"
       [[ -z "$process_state" || "$process_state" == *Z* ]] && break
       sleep 0.2
     done
     if [[ -n "$process_state" && "$process_state" != *Z* ]]; then
       echo "$label is still stopping. Retry after its active work finishes." >&2
       exit 1
     fi
   fi
  fi
  rm -f "$file" "$repo_root/.local/run/$label.started"
 fi
done
