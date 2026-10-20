# Cloud environment handoff

The application was built and validated in `/workspace/MediCare-AI`, using the existing isolated checkout. No worktree was created. The configured source repository is `rohitbiswas1/MediCare-AI`; use Git history and the remote to verify the published revision.

A reusable environment draft was saved with:

- `install_script`: runs `scripts/install.sh --ml` in this checkout using frozen locks.
- `start_skill`: retained-state guidance, service startup/stop/restart, readiness and functional checks, credential handling, and medical capability boundaries.
- Optional variable requirements: `SUPABASE_URL`, `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`.
- Optional proxy-secret requirements: `GOOGLE_MAPS_API_KEY` for `places.googleapis.com`, and `GEMINI_API_KEY` for `generativelanguage.googleapis.com`.
- Those two exact Google API domains were added by the secret-requirement save. Other network policy was preserved.
- The Render demo workflow additionally declares `RENDER_API_KEY` for `api.render.com`
  and allows `render.com` (documentation/schema) and `*.onrender.com` (deployment checks).
  These are saved requirements; no Render credential was available during local validation.

This confirmed a saved draft, not runtime activation, external deployment, or publication. Review and save the changes in environment settings, then publish the prepared environment through the product. Fresh-task restoration has not been independently verified.

The default development workflow needs no external key. For live Supabase, supply your project URL first, then configure project-specific auth/storage keys securely and allow its exact hostname. Never send keys in chat. For the interactive browser map, configure the referrer-restricted public browser key and allow its required Google Maps JS/static/font hosts in restricted browser environments. Do not enable production mode before completing the deployment safeguards and provider verification described in DEPLOYMENT.md.

The app, API, worker, scheduler, PostgreSQL, and Redis were left running after the validated startup. These processes must be restarted after restoring a snapshot. Local `.local/` files and Docker data volumes contain development state only; no patient datasets or medical weights were added.

The Render image `medicare-ai-render-demo:local` was also built and exercised
through `scripts/render_smoke.py`. Its disposable database, queue, container,
encrypted volume and test accounts were removed after the checks. For Render
deployment instructions and account prerequisites, see `RENDER.md`.
