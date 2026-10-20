# API usage

FastAPI exposes `/docs` and `/openapi.json`. The frontend proxies `/api/v1/<path>` to backend `/<path>`. Endpoint bodies are validated using Pydantic; malformed requests return 422 without echoing sensitive input.

All private endpoints require an HttpOnly session cookie. Unsafe requests additionally send `X-CSRF-Token` matching the readable `medicare_csrf` cookie. Login/register are exempt from the token but reject foreign browser origins. No patient resource may be fetched by simply knowing its UUID.

| Group | Routes |
| --- | --- |
| Auth | `POST /auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout` |
| Account | `GET/PATCH/DELETE /users/me`, `GET /users/me/summary`, `GET/PATCH /users/me/consent` |
| Reports | `POST /reports/upload`, `GET /reports`, `GET/DELETE /reports/{id}`, `POST /reports/{id}/analyze`, `GET /reports/{id}/analysis`, `/extraction`, `/download`, `/signed-url` |
| Prescriptions | `POST /prescriptions/upload`, `GET /prescriptions`, `GET /prescriptions/{id}`, `PATCH /prescriptions/{id}/confirm` |
| Catalog | `GET /medicines/search?q=`, `GET /medicines/{id}` |
| Pharmacies | `GET /pharmacies/nearby?q=` or `?lat=&lng=`, `GET /pharmacies/{id}`, `/inventory` |
| Admin | `GET /admin/metrics`, `/admin/model-versions`, `POST /admin/medicines`, `PUT /admin/pharmacies/{id}/inventory` |
| Operations | `GET /health`, `/capabilities` |

## Upload and review

Uploads are multipart forms with `file`, `consent=true`, and optional `report_type` (`document`, `blood_test`, `heart_rate`, `ecg`, `xray`). Prescriptions use the dedicated route and only PDF/JPG/PNG. Uploads return a report/prescription UUID. Poll its status while queued. Analysis is 409 until available. Failed jobs expose a safe message and can be retried. Deletion removes private blobs and dependent data; it is irreversible in the active store.

`GET /reports` accepts `limit` (1–100) and `offset`. Dashboard trends use the latest 20 completed reports and keep measurement names/units in separate series. Dashboard totals use server-side counts scoped to the authenticated user.

## Medicine import

Only UUIDs listed in `ADMIN_USER_IDS` are administrators; neither user-supplied role fields nor frontend visibility grants access. An administrator may POST a verified record with `generic_name`, `brand_name`, `strength`, `dosage_form`, `manufacturer`, `prescription_required`, `source_url`, `source_name`, and timezone-aware `verified_at`. The timestamp cannot be in the future. Use actual licensed data; the repository does not supply medical catalog claims. The application never independently recommends a substitution.

## Partner inventory boundary

The administrator endpoint is the initial partner-ingestion interface. A trusted server-side partner adapter maps a verified supplier record to existing pharmacy and medicine UUIDs, records `source_reference`, chooses `verified_in_stock` or `verified_out_of_stock`, and sets a timezone-aware expiry no more than 24 hours ahead. Expired records are returned as `availability_not_confirmed`.

Do not distribute an administrator credential directly to pharmacies. Before a multi-partner rollout, add per-partner scoped credentials, pharmacy ownership, revocation, signed ingestion records, and contractual freshness guarantees. Public Google Places results cannot populate this endpoint automatically.

## Error semantics

401: missing/expired auth; 403: CSRF/origin/role denial; 404: absent or unauthorized resource; 409: pending processing or conflict; 413: file size; 422: invalid/unsupported input; 429: rate limit; 503: unavailable required service. UI error states preserve these distinctions without displaying provider internals.
