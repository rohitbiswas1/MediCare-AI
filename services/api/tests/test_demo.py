from datetime import timedelta
from uuid import UUID

import pytest
from fastapi import Response

from app.auth import session_cookie
from app.config import Settings, settings
from app.db import SessionLocal
from app.jobs import purge_expired
from app.models import MedicalReport, now
from test_workflows import upload


def demo_settings(tmp_path, **overrides):
    values = {
        "app_mode": "demo",
        "database_url": "postgresql+psycopg://demo:example@database/demo",
        "app_secret": "synthetic-test-secret-at-least-32-characters",
        "allowed_origins": "https://demo.example.com",
        "local_data_dir": str(tmp_path),
    }
    values.update(overrides)
    return Settings(**values)


@pytest.mark.parametrize("origin", [
    "http://demo.example.com", "https://", "https://demo.example.com/path",
    "https://user@demo.example.com", "https://demo.example.com?query=1",
])
def test_public_demo_rejects_invalid_origins(tmp_path, origin):
    with pytest.raises(RuntimeError, match="exact HTTPS"):
        demo_settings(tmp_path, allowed_origins=origin).validate_runtime()


def test_demo_security_requirements(tmp_path):
    cfg = demo_settings(tmp_path)
    cfg.validate_runtime()
    assert cfg.secure_cookies
    assert not cfg.production
    assert cfg.storage_encryption_key
    with pytest.raises(RuntimeError, match="generated APP_SECRET"):
        demo_settings(tmp_path, app_secret="").validate_runtime()
    with pytest.raises(RuntimeError, match="Clinical inference"):
        demo_settings(tmp_path, inference_url="http://model").validate_runtime()
    with pytest.raises(RuntimeError, match="Production requires"):
        demo_settings(tmp_path, app_mode="production").validate_runtime()


def test_demo_session_cookies_are_secure(monkeypatch):
    monkeypatch.setattr(settings(), "app_mode", "demo")
    response = Response()
    session_cookie(response, "synthetic-token")
    cookies = response.headers.getlist("set-cookie")
    assert len(cookies) == 2
    assert all("Secure" in cookie and "SameSite=lax" in cookie for cookie in cookies)
    assert "HttpOnly" in cookies[0]


def test_demo_retention_removes_only_expired_documents(signed, monkeypatch):
    expired = upload(signed)
    active = upload(signed)
    with SessionLocal() as db:
        report = db.get(MedicalReport, UUID(expired))
        report.expires_at = now() - timedelta(days=1)
        db.commit()
    monkeypatch.setattr(settings(), "app_mode", "demo")
    assert purge_expired() == 1
    with SessionLocal() as db:
        assert db.get(MedicalReport, UUID(expired)) is None
        assert db.get(MedicalReport, UUID(active)) is not None
