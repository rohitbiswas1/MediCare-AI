# MediCare AI

To open the complete app locally, start Docker Desktop and run
`docker compose -f compose.local.yaml up --build -d --wait`, then open
`http://localhost:3000` on that computer. No hosting account is needed.
See [the local demo guide](docs/LOCAL-DEMO.md) for clone and startup instructions.

For a full interactive demo on Render, see [the Render deployment guide](docs/RENDER.md)
and the root [Blueprint](render.yaml). It includes the frontend, API, OCR worker,
PostgreSQL, Redis, and persistent encrypted storage. Render provisioning and its
charges require a connected account; the guide does not claim an existing live URL.

**Understand Your Health. Find Your Care.**

A working healthcare development monorepo for India: Next.js + FastAPI + PostgreSQL + Redis/Celery, private uploads, real OCR, source-grounded explanations, prescription review, a sourced medicine catalog, and pharmacy discovery adapters.

**This release is for development and research. Use synthetic documents only.** It does not diagnose, prescribe, change doses, or replace a qualified professional. No clinically validated ECG/X-ray weights, licensed datasets, medicine feed, or provider credentials are bundled.

## What works

| Area | Implemented behavior |
| --- | --- |
| Authentication | Supabase Auth integration; isolated local development accounts; Argon2id; HttpOnly sessions; CSRF; logout revocation; profile and account deletion |
| Reports | Validated PDF/PNG/JPEG/supported DICOM uploads; explicit consent; encrypted local or private Supabase storage; asynchronous processing; history; downloads; deletion |
| Extraction | Real Tesseract image OCR, PyMuPDF text/scanned PDFs, basic OpenCV quality checks; exact source quotations; no invented units or measurements |
| Explanations | Conservative printed-reference comparisons; English/Hindi/Bengali templates and safety notices; optional Gemini selection from approved templates only |
| Prescriptions | OCR transcription; conservative catalog-backed name/strength/form/instruction candidates; editable human confirmation; no guessed unreadable medicine |
| Catalog | Authenticated generic/brand search; administrator import with source URL, verification date, prescription classification; no seeded clinical records or prices |
| Pharmacies | Google Places search by address or user-permitted location; optional interactive map; contact/directions; source-backed inventory with expiry; default stock unconfirmed |
| Interface | All requested screens, responsive layouts, dark mode, accessible form labels, language selector, real-data Recharts trends, useful empty states |
| Research | PTB-XL/CheXpert preparation, patient-level splits, CNN and Hugging Face PatchTST ECG models, MONAI DenseNet X-ray model, reproducible training, calibration, subgroup metrics, fixed-artifact external evaluation |
| Security | API ownership checks plus forced PostgreSQL RLS; private-table grants; audit/access records; rate limits; request validation; production startup guards |
| Operations | Alembic migrations, containers, Compose, GitHub Actions, health checks, retention scheduler, reusable install/start scripts |

### Explicit limits

- Clinical ECG and X-ray inference is **unavailable** in the patient application. Paper ECG images are never treated as raw waveforms. DICOM containers can be stored; pixel decoding/inference and automated view classification are not enabled.
- The research service accepts supported raw ECG NPZ and AP/PA image inputs only when verified experimental artifacts are explicitly enabled. Production mode rejects these artifacts. No heatmaps are fabricated.
- English OCR is installed. Core navigation/forms/consent and evidence explanations have Hindi and Bengali translations; original document text, medicine names, and numerical values remain unchanged. Support/legal/deployment material and some secondary interface copy remain English. Translation requires clinical review before patient use.
- Development uploads get structural safety checks unless ClamAV is configured. Production requires a reachable malware scanner, verified private storage, TLS database/Redis, Supabase auth, and a non-superuser `NOBYPASSRLS` database role.
- Live Supabase, Gemini, Google Maps, and partner inventory verification require your service configuration. No provider calls are claimed as tested without credentials.
- The catalog starts empty. Import only licensed, reviewed records with traceable sources. Google business listings do not establish medicine stock.
- This is not a regulatory approval, clinical validation, security certification, or published deployment.

## Run locally

Prerequisites: Node 22+ (24 recommended), Python 3.12, `uv`, Docker with Compose, and Tesseract OCR 5 with English data. Linux is the validated development platform. Install Tesseract using your OS package manager, or use the application containers.

```bash
# From the repository root; uses existing checkout, no worktree needed.
bash scripts/install.sh          # frozen JS/Python installs, DB/Redis, migrations
bash scripts/dev.sh              # API, OCR worker, retention scheduler, frontend
```

The frontend uses port 3000, API port 8000, PostgreSQL 5432, and Redis 6379. OpenAPI is served at the API's `/docs` and `/openapi.json`. The browser accesses `/api/v1/*` through the same-origin Next.js proxy. Create an account in the registration screen; no shared default login is provided.

A root `.env` is optional for local development; defaults are in `services/api/app/config.py`. Copy `.env.example` to `.env` to configure integrations, preserving any existing file. Never commit `.env` or keys. `.local/` contains generated development encryption/session keys, encrypted documents, process logs, and PID files. Losing the local storage key makes existing documents unreadable. Do not use this local mode for real patient data.

```bash
bash scripts/stop.sh             # stops processes recorded by dev.sh
# Stops data services while preserving their volumes:
docker compose stop postgres redis
```

Node dependencies, Python environments, and generated files can persist in a cloud snapshot. Processes do not; run `scripts/dev.sh` again after restore. Fresh Docker volumes are initialized by the install/start migrations.

### All application services in Docker

```bash
cp .env.example .env             # only if .env does not already exist
docker compose up -d --wait postgres redis
docker compose --profile app build
# Apply migrations before the application starts:
docker compose --profile app run --rm api uv run --frozen --no-dev alembic upgrade head
docker compose --profile app up -d api worker beat
npm ci
npm run dev
```

Compose defaults are local development settings. Production uses managed services and separate identities; see [deployment](docs/DEPLOYMENT.md). Enable ClamAV with the `antivirus` profile and set `CLAMAV_HOST` to the reachable scanner hostname; allow its official signature updates. ClamAV startup/download readiness is not implied by a container PID.

## Verify

```bash
npm run lint
npm run typecheck
npm run build
(cd services/api && uv run --frozen python -m pytest -q)
# With API, worker, PostgreSQL, and Redis running:
services/api/.venv/bin/python scripts/smoke.py
services/api/.venv/bin/python scripts/check_rls.py
# With frontend running; use a Playwright-managed Chromium or the installed system binary:
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium npm run test:e2e
```

The smoke test performs real PDF/image extraction using synthetic content, verifies isolation, and deletes its accounts/documents. `check_rls.py` creates and removes a temporary non-superuser DB role; use only a disposable local development DB with role-creation permission. Never run it against a patient database.

Browser tests cover desktop/mobile registration, empty states, language switching, dark mode, role denial, queued OCR, and report deletion. Tests preserve screenshots/traces on failure; the fixtures contain synthetic data only. Results are described in [validation](docs/VALIDATION.md).

For research:

```bash
bash scripts/install.sh --ml
uv run --frozen --project ml python -m pytest tests/test_ml.py -q
```

See [ML instructions](ml/README.md) for real authorized datasets and training/evaluation commands. Synthetic engineering tests are not medical performance evidence.

## API and data

[Architecture](docs/ARCHITECTURE.md) describes trust boundaries and processing states. [API usage](docs/API.md) explains endpoint groups, catalog imports, and inventory verification. The full schema is in `services/api/app/models.py`; Alembic revisions create all 14 requested tables plus migration metadata.

Generate TypeScript contracts from a running API:

```bash
npm run generate --workspace packages/shared-types
```

## Before enabling external services or real-patient use

Read [deployment](docs/DEPLOYMENT.md), [privacy and security](docs/SECURITY.md), and the [model card requirements](ml/MODEL_CARD.md). Supply credentials through your environment/secret manager, validate service contracts with your accounts, configure data residency/retention/backups, publish your operator and grievance contact, perform clinical/translation/security reviews, and assess applicable DPDP and CDSCO obligations. The app deliberately refuses unsafe production configurations.

No commits have been pushed, infrastructure deployed, or cloud snapshot published by the setup scripts.

For an optimized local frontend after `npm run build`, stop the existing processes and run `MEDICARE_WEB_MODE=production bash scripts/dev.sh`. This changes the frontend serving mode only; the API remains in the explicitly configured application mode. Keep using development data unless the full production review and configuration are complete.
