import secrets
from datetime import timedelta
from uuid import UUID
import httpx
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from .config import settings
from .db import get_db, set_owner
from .models import User, Profile, now

password_hasher = PasswordHasher()


def verify_password(encoded, password):
    try:
        return bool(encoded) and password_hasher.verify(encoded, password)
    except VerificationError:
        return False


def session_cookie(response: Response, token: str, refresh: str | None = None):
    cfg = settings()
    response.set_cookie(
        "medicare_session",
        token,
        httponly=True,
        secure=cfg.secure_cookies,
        samesite="lax",
        max_age=3600,
        path="/",
    )
    response.set_cookie(
        "medicare_csrf",
        secrets.token_urlsafe(32),
        httponly=False,
        secure=cfg.secure_cookies,
        samesite="lax",
        max_age=7 * 86400,
        path="/",
    )
    if refresh:
        response.set_cookie(
            "medicare_refresh",
            refresh,
            httponly=True,
            secure=cfg.secure_cookies,
            samesite="lax",
            max_age=7 * 86400,
            path="/api/v1/auth",
        )


def local_token(user):
    return jwt.encode(
        {
            "sub": str(user.id),
            "exp": now() + timedelta(hours=1),
            "iat": now(),
            "iss": "medicare-local",
            "aud": "medicare-api",
            "version": user.session_version,
        },
        settings().app_secret,
        algorithm="HS256",
    )


def supabase_request(path, payload=None, token=None, method="POST", admin=False):
    cfg = settings()
    if not cfg.supabase_url or not cfg.supabase_anon_key:
        raise HTTPException(503, "Supabase authentication is not configured.")
    key = cfg.supabase_service_role_key if admin else cfg.supabase_anon_key
    headers = {"apikey": key, "Authorization": f"Bearer {token or key}"}
    try:
        result = httpx.request(
            method,
            f"{cfg.supabase_url.rstrip('/')}/auth/v1/{path}",
            json=payload,
            headers=headers,
            timeout=15,
        )
    except httpx.HTTPError:
        raise HTTPException(503, "Authentication provider is temporarily unavailable.")
    if result.status_code >= 400:
        raise HTTPException(
            401 if result.status_code < 500 else 503,
            "Authentication failed. Check your details and email verification status.",
        )
    return result.json() if result.content else {}


def current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("medicare_session")
    if not token:
        raise HTTPException(401, "Please sign in to continue.")
    try:
        if settings().auth_provider == "supabase":
            identity = supabase_request("user", token=token, method="GET")
            user_id = UUID(identity["id"])
        else:
            claims = jwt.decode(
                token,
                settings().app_secret,
                algorithms=["HS256"],
                audience="medicare-api",
                issuer="medicare-local",
            )
            user_id = UUID(claims["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(401, "Your session has expired. Please sign in again.")
    set_owner(db, user_id)
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(401, "Account not found.")
    if settings().auth_provider == "local" and claims.get("version") != user.session_version:
        raise HTTPException(401, "Session has been revoked.")
    return user


def admin_user(user: User = Depends(current_user)):
    configured = {x.strip() for x in settings().admin_user_ids.split(",") if x.strip()}
    if str(user.id) not in configured:
        raise HTTPException(403, "Administrator access required.")
    return user


def user_view(db, user):
    profile = db.scalar(select(Profile).where(Profile.owner_id == user.id))
    configured = {x.strip() for x in settings().admin_user_ids.split(",")}
    return {
        "id": user.id,
        "email": user.email,
        "name": profile.name if profile else "",
        "language": profile.language if profile else "en",
        "role": "admin" if str(user.id) in configured else "user",
        "third_party_ai": profile.third_party_ai if profile else False,
        "mode": settings().app_mode,
    }
