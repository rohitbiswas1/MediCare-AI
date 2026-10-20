# Worker process

The queue implementation is `services/api/app/jobs.py`, shared with the API so schema and processing versions cannot drift. Run from `services/api`:

```bash
uv run --frozen celery -A app.jobs:celery worker --loglevel=WARNING --concurrency=2
uv run --frozen celery -A app.jobs:celery beat --loglevel=WARNING --schedule ../../.local/beat-schedule
```

Redis messages contain report and owner UUIDs only. Document content remains in private storage. Run one beat scheduler. The hourly retention task needs a separately controlled database identity able to enumerate expired reports; ordinary request workers use ownership context. Set process memory limits (start with 1 GiB per OCR worker), monitor queue age and failed reports, and alert on retention failures. Never log OCR text or provider request bodies. Live processes must restart after a cloud snapshot restore.
