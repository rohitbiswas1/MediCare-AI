# Validation record

Validated in this cloud workspace on 20 October 2026. All application fixtures were synthetic and created accounts/documents were deleted by the tests. This validates software behavior, not clinical performance or regulatory compliance.

| Check | Result |
| --- | --- |
| Frozen installation | `scripts/install.sh --ml` completed; Node dependencies and both Python environments installed; PostgreSQL/Redis healthy; Alembic migrations applied |
| Frontend lint / TypeScript | Passed |
| Production frontend build | Passed, including all requested routes |
| API suite | 39 passed; no skipped tests; includes demo HTTPS origin/cookie guards and retention; one upstream Starlette test-client deprecation warning |
| ML engineering suite | 5 passed, including real CNN/PatchTST/MONAI forward passes, patient isolation, metrics, one-epoch synthetic training/calibration, and checksum rejection |
| Browser suite | 6 passed across Chromium desktop and Pixel 7 viewport: registration, empty states, languages, dark mode, role denial, real queued OCR, deletion, prescription confirmation, consent persistence, account erasure |
| Live host smoke | Passed with actual PostgreSQL, Redis/Celery, PDF extraction, Tesseract image OCR, ownership/CSRF, download, and erasure |
| Database authorization | Passed using a real temporary non-superuser PostgreSQL role: other owners hidden and missing owner context denied |
| Container build | Passed; dependency signatures and TLS verification preserved; trusted cloud CA supplied as a temporary BuildKit secret |
| Container runtime | Non-root API and worker passed the same live OCR/auth/storage/deletion smoke test using a shared encrypted volume; test containers and volume removed |
| Production npm dependency audit | Zero reported vulnerabilities at the time of this run; this is not a comprehensive security review |
| Startup lifecycle | Start, repeat-start, stop, and restart verified; process identity includes boot ID/start time to avoid stale PID reuse |
| Render demo image | Optimized standalone frontend + API + worker + scheduler built successfully |
| Render image integration | Passed `scripts/render_smoke.py` over locally verified HTTPS: generated samples, secure cookies, actual OCR, isolated non-superuser PostgreSQL, restart persistence, owner isolation, deletion and worker-failure shutdown |
| Render Blueprint | YAML parsing, referenced resources and Docker paths checked locally; Render server validation/provisioning awaits account access |
| Local Docker launch | `compose.local.yaml` built and started with all three containers healthy; frontend, API, OCR worker and scheduler run together behind a loopback-only port |
| Local Docker workflows | All 6 desktop/mobile browser tests and the live PDF/image OCR smoke passed against the packaged app; restart preserved the session, account, extracted results and encrypted document |
| Shared launcher regression | Render image HTTPS, secure cookies, OCR, restart persistence and worker-failure shutdown checks passed after sharing supervision with the local launcher |

## Integration scope

Supabase Auth/Storage, Google Places/Maps, and Gemini adapters are implemented. Contract tests use controlled responses where necessary; no live-provider verification is claimed because credentials were absent. Local authentication and encrypted storage were exercised instead. English OCR was exercised against generated images and PDFs.

There are no clinically validated ECG/X-ray weights, authorized real research datasets, live medicine feed, or partner-stock records in this workspace. No clinical training/evaluation, regulator approval, actual pharmacy stock verification, or model heatmap validation occurred. Research tests use synthetic data only and their scores must not be cited as medical performance.

The ClamAV integration and production fail-closed checks are implemented; live antivirus signatures/scanning were not provisioned in this development run. Uploads here use structural checks. No real patient records should be uploaded.

GitHub Actions configuration is included; remote CI status has not been verified.
The local Docker stack was tested on Linux in Codex cloud; Docker Desktop on
macOS/Windows has not been independently tested. See `docs/LOCAL-DEMO.md` for the
local launch command and persistent volume behavior.
No Render deployment or cloud environment publication is claimed by these local
tests. A saved environment draft is separate from publication and from validation
in a fresh task. See `docs/RENDER.md` for the deployment and paid resource choices.
