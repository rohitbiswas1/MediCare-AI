from functools import lru_cache
from pathlib import Path
import os
import secrets
from cryptography.fernet import Fernet
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(ROOT / ".env", ".env"), extra="ignore")
    app_mode: str = "development"
    database_url: str = "postgresql+psycopg://medicare:local-development-only@127.0.0.1:5432/medicare"
    migration_database_url: str = ""
    redis_url: str = "redis://127.0.0.1:6379/0"
    local_data_dir: str = str(ROOT / ".local")
    auth_provider: str = "local"
    storage_provider: str = "local"
    app_secret: str = ""
    storage_encryption_key: str = ""
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_storage_bucket: str = "medical-reports"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    google_maps_api_key: str = ""
    clamav_host: str = ""
    clamav_port: int = 3310
    admin_user_ids: str = ""
    retention_days: int = 90
    max_upload_bytes: int = 15 * 1024 * 1024
    inference_url: str = ""

    @property
    def production(self):
        return self.app_mode == "production"

    @property
    def secure_cookies(self):
        return self.app_mode in {"demo", "production"}

    @property
    def origins(self):
        return [x.strip() for x in self.allowed_origins.split(",") if x.strip()]

    def validate_runtime(self):
        if self.app_mode not in {"development", "test", "demo", "production"}:
            raise RuntimeError("APP_MODE must be development, test, demo, or production")
        if self.auth_provider not in {"local", "supabase"} or self.storage_provider not in {
            "local",
            "supabase",
        }:
            raise RuntimeError("Unsupported authentication or storage provider")
        if self.app_mode == "demo":
            from urllib.parse import urlsplit

            if self.auth_provider != "local" or self.storage_provider != "local":
                raise RuntimeError("The standalone demo requires local auth and encrypted local storage")
            if len(self.app_secret) < 32 or not self.database_url.startswith("postgresql"):
                raise RuntimeError("The demo requires PostgreSQL and a generated APP_SECRET")
            if not self.origins or any(
                urlsplit(origin).scheme != "https"
                or not urlsplit(origin).hostname
                or urlsplit(origin).path
                or urlsplit(origin).query
                or urlsplit(origin).fragment
                or urlsplit(origin).username
                for origin in self.origins
            ):
                raise RuntimeError("The demo requires exact HTTPS frontend origins")
            if self.inference_url:
                raise RuntimeError("Clinical inference is unavailable in the demo")
        if self.production:
            required = [
                self.supabase_url,
                self.supabase_anon_key,
                self.supabase_service_role_key,
                self.app_secret,
                self.clamav_host,
            ]
            if self.auth_provider != "supabase" or self.storage_provider != "supabase" or not all(required):
                raise RuntimeError(
                    "Production requires Supabase auth/private storage, APP_SECRET, and ClamAV"
                )
            if (
                not self.origins
                or not self.database_url.startswith("postgresql")
                or not all(x.startswith("https://") for x in self.origins)
            ):
                raise RuntimeError("Production requires PostgreSQL and HTTPS origins")
            if not self.supabase_url.startswith("https://"):
                raise RuntimeError("Supabase must use HTTPS in production")
            from sqlalchemy.engine import make_url

            if make_url(self.database_url).query.get(
                "sslmode"
            ) != "verify-full" or not self.redis_url.startswith("rediss://"):
                raise RuntimeError(
                    "Production requires PostgreSQL sslmode=verify-full and TLS Redis (rediss://)"
                )
            if len(self.app_secret) < 32:
                raise RuntimeError("APP_SECRET must contain at least 32 random characters")
        if not self.app_secret:
            self.app_secret = self._local_key("session.key", lambda: secrets.token_urlsafe(48))
        if self.storage_provider == "local" and not self.storage_encryption_key:
            self.storage_encryption_key = self._local_key(
                "storage.key", lambda: Fernet.generate_key().decode()
            )

    def _local_key(self, filename, generator):
        directory = Path(self.local_data_dir)
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = directory / filename
        import fcntl

        fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
        with os.fdopen(fd, "r+") as file:
            fcntl.flock(file, fcntl.LOCK_EX)
            existing = file.read().strip()
            if existing:
                return existing
            value = generator()
            file.write(value)
            file.flush()
            os.fsync(file.fileno())
            return value


@lru_cache
def settings():
    value = Settings()
    value.validate_runtime()
    return value
