# Run the full app on your computer

Install and start Docker Desktop (or Docker Engine with Compose on Linux).
Everything else runs in containers: frontend, API, OCR worker, scheduler,
PostgreSQL and Redis. No Node/Python installation, hosting account, API key, or
payment to Render is needed. The first build downloads dependencies.

```bash
git clone https://github.com/rohitbiswas1/MediCare-AI.git
cd MediCare-AI
docker compose -f compose.local.yaml up --build -d --wait
```

If you already cloned the repository, use that checkout and pull the latest
changes instead of cloning again. Preserve any local changes first.

Open **http://localhost:3000** on the same computer. Create an account, download
a sample document from the banner, upload it and explore the results and history.
This runs the actual application and real OCR. Use synthetic documents only.
Clinical model inference and unconfigured external integrations remain unavailable.

If port 3000 is occupied:

```bash
MEDICARE_LOCAL_PORT=3001 docker compose -f compose.local.yaml up --build -d --wait
```

Then open `http://localhost:3001`. Keep that port setting when recreating the app.
The frontend is bound only to your computer's loopback interface; the database
and queue have no published host ports.

Stop while preserving accounts and documents:

```bash
docker compose -f compose.local.yaml stop
```

Start again:

```bash
docker compose -f compose.local.yaml up -d --wait
```

Inspect startup if needed:

```bash
docker compose -f compose.local.yaml logs --tail=80 app
```

Docker volumes hold the database, queue, encrypted uploads and generated
session/encryption keys. `docker compose ... down` preserves those volumes.
Adding `--volumes` erases them, including all local accounts and documents.

The container stack is verified in Codex's Linux Docker environment. Native
Docker Desktop execution on macOS/Windows has not been independently tested.
The commands deliberately run application processes inside Linux containers
instead of relying on host-specific shell startup scripts.

## Codex cloud

The development app can also run with `bash scripts/dev.sh` in the prepared cloud
workspace. That workspace's localhost belongs to the cloud machine. A localhost
address in your Mac's browser reaches your Mac; it does not reach the cloud app.
This session currently has no public port-forwarding capability.
