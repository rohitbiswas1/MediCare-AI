# Deployment guide

No external deployment is performed by these files. Vercel, Supabase, Google, container hosting, antivirus signature access, and licensed datasets must be provisioned separately.

## 1. Database and authentication

Create a Supabase project in an approved region. Enable email/password Auth, email confirmation, appropriate password policy, and your production site/redirect URLs. Email confirmation returns the user to the site; they can then sign in. Decide operator-supported account recovery before launch.

Use a privileged migration identity only for Alembic. Configure `MIGRATION_DATABASE_URL` separately from `DATABASE_URL`. Run `uv run --frozen alembic upgrade head` from `services/api`. Create an application login with `NOSUPERUSER NOBYPASSRLS`, grant required application-table CRUD, and keep its credentials in the secret manager. The API checks the connected role at production startup. RLS requires transaction-local `app.user_id`, set by the API after authentication. Do not enable a direct browser database client for these tables.

Apply `infrastructure/deployment/supabase.sql` to create the private bucket. Supabase URL, anon key, service-role key, and bucket name are API environment settings; the service-role key must never reach the frontend. The API verifies that the bucket is private on production startup. Review Supabase Auth/Storage email, region, retention, audit, processor, and backup settings with your operator.

## 2. API, queue, worker, retention

Build `infrastructure/docker/api.Dockerfile` and publish the resulting image through your own registry workflow. Run it as the non-root image user, with a read-only root filesystem where supported, a small writable runtime volume, CPU/memory limits, and HTTPS termination. Limit ingress to the frontend proxy/trusted clients. Do not expose Redis or PostgreSQL publicly.

Required production settings:

- `APP_MODE=production`, `AUTH_PROVIDER=supabase`, `STORAGE_PROVIDER=supabase`.
- `DATABASE_URL`: PostgreSQL URL with `sslmode=verify-full`; supply your provider's CA through supported trust configuration when needed.
- `REDIS_URL`: authenticated `rediss://` URL with certificate verification.
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`.
- `APP_SECRET`: at least 32 securely generated characters, kept in the secret manager.
- `ALLOWED_ORIGINS`: exact HTTPS frontend origin(s).
- `CLAMAV_HOST`, `CLAMAV_PORT`: private reachable, updated scanner. A scanner failure blocks uploads.
- `RETENTION_DAYS`: approved document retention; initially 90.
- `ADMIN_USER_IDS`: explicitly provisioned operator UUIDs; empty means no admins.

Run API and Celery worker as separate processes from the same image. Use two OCR worker processes initially and measure memory/latency before increasing concurrency. Configure one Celery beat scheduler and a separately controlled retention worker identity that can enumerate expired rows. The ordinary request/processing role must not bypass RLS. Route retention jobs to a dedicated queue/worker in production before granting that identity broader access. The local Compose configuration uses a disposable development superuser and is not a production authorization example.

The hourly retention task removes blobs before database rows; failures remain retryable. Alert on queue age, failed jobs, scanner status, database availability, API 5xx rates, and retention backlog. Use request IDs and aggregate metrics. Disable request-body, auth-header, query-string, OCR-text, and signed-URL logging. Uvicorn access logs are disabled by the provided command.

The application intentionally does not trust arbitrary forwarded IP headers. Configure trusted proxy hops and edge rate limits for a real deployment; otherwise the API's safe default rate limit aggregates clients behind the same proxy. Admin report counts also depend on the DB role's visibility; use a reviewed aggregate-only reporting function if operators need cross-tenant totals under RLS.

## 3. Vercel frontend

Import the monorepo and set Root Directory to `apps/web`. Copy the settings in `infrastructure/deployment/vercel.json` into the project settings (or use it as the project's config). Install from the monorepo root with `npm ci`, build with `npm run build`, and set `API_INTERNAL_URL` to the private/authenticated API ingress reachable by Vercel over HTTPS. This variable is server-only. Set `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` only if the map is enabled; browser map keys must be restricted by HTTP referrer and API scope.

Use the exact frontend URL in `ALLOWED_ORIGINS`. Verify Secure/HttpOnly/SameSite cookies and CSRF through the final same-origin proxy. Test auth renewal and logout using a real Supabase account. The initial CSP supports Next.js and Google Maps; assess a request-nonce policy for your deployment and eliminate development-only eval allowances. No patient data is serialized into public static pages.

## 4. Google Maps and optional Gemini

Enable Places API (New), billing/quota controls, and a server-restricted `GOOGLE_MAPS_API_KEY`. Server requests go to `places.googleapis.com`; maps use Google Maps JS hosts. Test both address and device-location searches. The UI requests location only after an explicit click and offers manual input. Follow Google Maps attribution, storage/refresh, and data-retention terms; cached business records must be refreshed/expired under your approved policy before launch.

Gemini is optional. `GEMINI_API_KEY` is sent as a header to `generativelanguage.googleapis.com`. It receives only an array of index/comparison-template keys after explicit consent. Output must exactly match the approved selection; otherwise deterministic templates are used. No provider-generated diagnosis or new measurement can enter an explanation through this adapter. Do not broaden it to identifiable records without a separate lawful-basis, consent, processor, and clinical-safety assessment.

## 5. Research inference and clinical release

The included inference image is CPU-based and private. GPU training requires a matching NVIDIA driver/runtime and CUDA PyTorch environment; do not use the CPU-only research lock for GPU performance claims. Keep inference disabled unless running an isolated research evaluation. No clinical release switch exists in this code.

Before patient deployment, complete external validation, calibration, subgroup assessment, clinician review, privacy/security testing, incident drills, operational support, translation review, and applicable medical-device/regulatory assessment. Document the intended use and exclusions. These prerequisites cannot be replaced by synthetic unit tests.

## Build networks and verification

For a build environment with an outbound proxy, pass the existing Docker predefined proxy build arguments without printing their values. Some cloud Docker bridges cannot resolve external DNS; a supported host-network build may be required. Preserve package signatures, artifact hashes, and TLS verification. If your organization uses a TLS inspection CA, supply that approved CA using a BuildKit secret rather than disabling verification or committing it to the image/repository. Container-build verification status is recorded in `docs/VALIDATION.md`.

## Backups and release operations

Keep migrations backward-compatible where possible, take encrypted backups, verify restores, and define backup deletion schedules consistent with the privacy notice. Preserve local encrypted-storage keys only in development; production uses managed encryption and access controls. Rotate provider keys, revoke compromised sessions, and deploy versioned images. Never put real patient fixtures in CI, screenshots, traces, issue trackers, or model experiments.

In this cloud workspace, `python scripts/build_container.py` supplies existing proxy DNS and its approved CA to Docker without printing proxy credentials or retaining the CA in the image. That helper and the resulting API image were exercised, including a non-root container OCR smoke run. On an ordinary machine, use the standard Docker build command.
