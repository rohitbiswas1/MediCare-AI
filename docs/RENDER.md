# Render interactive demo

The root `render.yaml` provisions the complete synthetic-data demo. It is not a
clinical deployment. No diagnostic model or pharmacy inventory is fabricated.

## Resources to review

| Resource | Render configuration |
| --- | --- |
| Web service | Standard, one instance, Oregon; built from `infrastructure/docker/render-demo.Dockerfile` |
| PostgreSQL | Basic 256 MB, Oregon; external IP access disabled |
| Key Value (Redis compatible) | Starter, Oregon, `noeviction`; external IP access disabled |
| Persistent disk | 1 GB at `/var/data` for encrypted documents and encryption key |

These are paid resources. Render displays current charges before deployment;
review that total in your account. There are no Google or Supabase charges for
the default demo. Delete the demo resources from Render when finished to stop
ongoing charges.

## Deploy

Once this repository is available on GitHub:

[Deploy to Render](https://render.com/deploy?repo=https://github.com/rohitbiswas1/MediCare-AI)

1. Sign in to Render and authorize access to `rohitbiswas1/MediCare-AI`.
2. Select the workspace, review the Blueprint and resource charges, and deploy.
3. Wait for the database, queue, and web service to become healthy. The web
   service's **onrender.com URL** is the live demo URL. It cannot use chatgpt.com.
4. Create an account using a test email and a password of at least 12 characters.
   Download the sample report or prescription from the banner and upload it.
   Explore OCR results, prescription review, history, profile, and privacy settings.

The Blueprint generates the session secret. Render supplies `RENDER_EXTERNAL_URL`;
the launcher uses it as the exact allowed origin. No credentials belong in Git
or chat. An optional `RENDER_API_KEY`, supplied securely in Codex environment
settings for `api.render.com`, allows an agent to inspect/manage the deployment.
It is not an application variable and must not be placed on the public web service.

## Runtime and persistence

The frontend, loopback-only API, one OCR worker, and retention scheduler run as
supervised processes in one non-root container. The launcher applies migrations,
checks API/database/queue readiness, then starts the optimized Next.js server.
If a child exits, the container exits so Render can restart it. SIGTERM stops all
children. The API's private files are outside the frontend's public directory.

One instance is intentional: Render disks cannot be shared by separate services.
The API and OCR worker therefore use the same encrypted disk. PostgreSQL and
Redis remain managed services on Render's private network. Do not scale this
Blueprint horizontally. This arrangement may have brief deployment downtime.

Uploads expire after one day; an hourly scheduler deletes expired documents
using owner-scoped database transactions. Accounts remain until deleted through
Privacy settings. Preserve the disk's encryption key with its files; deleting
the disk loses the ability to decrypt them. A service restart preserves both.

Demo mode requires HTTPS origins and Secure cookies, uses local account
authentication, and does not enable the patient-production configuration.
Upload structural validation is enabled; ClamAV is not included. Use synthetic
documents only. The separate production safeguards in `docs/DEPLOYMENT.md`
continue to require Supabase, antivirus scanning, TLS and reviewed database roles.

Google pharmacy search and Gemini require their respective credentials.
ECG/X-ray diagnostic inference remains unavailable pending validated models.
Medicine catalog and inventory stay empty until sourced data is added.

## Verify the actual deployment

The final URL must pass `/api/v1/health` and a browser sign-up/upload/OCR flow.
Check Secure, HttpOnly, SameSite cookies and cross-account report isolation.
An image build, a saved Blueprint, or a queued deployment is not evidence that
the public URL works.

For a standard Docker build:

```bash
docker build -f infrastructure/docker/render-demo.Dockerfile -t medicare-demo .
```

In the managed Codex environment, use the existing proxy and approved CA:

```bash
python scripts/build_container.py \
  --dockerfile infrastructure/docker/render-demo.Dockerfile \
  --tag medicare-ai-render-demo:local
```

With the development Compose database running, test the complete image:

```bash
services/api/.venv/bin/python scripts/render_smoke.py
```

The test uses a temporary trusted TLS certificate without disabling verification,
a disposable non-superuser PostgreSQL role/database, a separate Redis container,
and its own encrypted volume. It checks OCR, secure cookies, restart persistence,
ownership and worker failure handling, then removes its resources.
