from contextlib import asynccontextmanager
import hashlib
import secrets
import time
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from .config import settings
from .db import engine
from .routes_auth import router as auth_router
from .routes_reports import router as report_router
from .routes_catalog import router as catalog_router

cfg = settings()
redis = Redis.from_url(cfg.redis_url, socket_connect_timeout=2, socket_timeout=2)


@asynccontextmanager
async def lifespan(app):
    cfg.validate_runtime()
    if cfg.production:
        from .storage import verify_private_bucket, scan_malware

        with engine.connect() as connection:
            role = connection.execute(
                text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname=current_user")
            ).one()
            if role[0] or role[1]:
                raise RuntimeError("Production API requires a non-superuser NOBYPASSRLS database role")
        verify_private_bucket()
        scan_malware(b"MediCare startup scanner readiness check")
    yield


app = FastAPI(
    title="MediCare AI API",
    version="0.1.0",
    lifespan=lifespan,
    description="Informational report extraction. No clinically validated diagnostic model is deployed.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)


@app.middleware("http")
async def security(request: Request, call_next):
    request_id = secrets.token_hex(8)
    mutating = request.method in {"POST", "PUT", "PATCH", "DELETE"}
    if mutating:
        origin = request.headers.get("origin")
        if origin and origin not in cfg.origins:
            return JSONResponse({"detail": "Untrusted request origin."}, status_code=403)
        exempt = request.url.path in {"/auth/login", "/auth/register"}
        if not exempt:
            cookie = request.cookies.get("medicare_csrf", "")
            header = request.headers.get("x-csrf-token", "")
            if not cookie or not secrets.compare_digest(cookie, header):
                return JSONResponse({"detail": "Missing or invalid CSRF token."}, status_code=403)
        size = request.headers.get("content-length", "")
        if size.isdigit() and int(size) > cfg.max_upload_bytes + 1024 * 1024:
            return JSONResponse({"detail": "Request exceeds the upload size limit."}, status_code=413)
    if request.url.path != "/health" and cfg.app_mode != "test":
        identity = request.client.host if request.client else "unknown"
        digest = hashlib.sha256(identity.encode()).hexdigest()[:24]
        is_auth = request.url.path in {"/auth/login", "/auth/register"}
        try:
            key = f"medicare:rate:{digest}:{'auth' if is_auth else 'api'}:{int(time.time()) // 60}"
            count = redis.incr(key)
            if count == 1:
                redis.expire(key, 65)
            if count > (15 if is_auth else 240):
                return JSONResponse(
                    {"detail": "Too many requests. Please try again in a minute."},
                    429,
                    headers={"Retry-After": "60"},
                )
        except RedisError:
            return JSONResponse({"detail": "Request protection is temporarily unavailable."}, 503)
    try:
        response = await call_next(request)
    except Exception as exc:
        logging.getLogger(__name__).error(
            "request_failed type=%s request_id=%s", type(exc).__name__, request_id
        )
        response = JSONResponse({"detail": "An unexpected error occurred.", "request_id": request_id}, 500)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "same-origin"
    if cfg.secure_cookies:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.get("/health")
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        redis.ping()
    except Exception:
        return JSONResponse({"status": "unavailable"}, status_code=503)
    return {"status": "ok", "mode": cfg.app_mode, "database": "connected", "queue": "connected"}


@app.get("/capabilities")
def capabilities():
    return {
        "mode": cfg.app_mode,
        "authentication": cfg.auth_provider,
        "storage": cfg.storage_provider,
        "ocr": "tesseract",
        "ocr_languages": ["en"],
        "malware_scan": "clamav" if cfg.clamav_host else "structural_checks_only",
        "gemini": bool(cfg.gemini_api_key),
        "pharmacy_discovery": bool(cfg.google_maps_api_key),
        "ecg": "unavailable",
        "xray": "unavailable",
        "clinical_use": False,
        "retention_days": cfg.retention_days,
        "training_on_uploads": False,
    }


app.include_router(auth_router)
app.include_router(report_router)
app.include_router(catalog_router)


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    # Avoid echoing credentials or medical text from rejected input in responses.
    return JSONResponse(
        {"detail": [{"loc": err["loc"], "msg": err["msg"], "type": err["type"]} for err in exc.errors()]},
        status_code=422,
    )
