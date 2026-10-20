"""Run the complete local Docker demo; no hosting account or external API key needed."""
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

from render_start import run


def configuration():
    env = os.environ.copy()
    if env.get("APP_MODE") != "development" or env.get("RENDER_EXTERNAL_URL"):
        raise RuntimeError("Use the Render launcher for hosted deployments")
    if env.get("AUTH_PROVIDER") != "local" or env.get("STORAGE_PROVIDER") != "local":
        raise RuntimeError("The local demo requires local authentication and encrypted storage")
    origins = env.get("ALLOWED_ORIGINS", "").split(",")
    for origin in origins:
        parsed = urlsplit(origin.strip())
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
            or parsed.username
            or parsed.password
            or parsed.path
            or parsed.query
            or parsed.fragment
        ):
            raise RuntimeError("Local demo origins must be exact HTTP loopback addresses")
    if not env.get("DATABASE_URL", "").startswith("postgresql+psycopg://"):
        raise RuntimeError("The local demo requires its configured PostgreSQL service")
    if not env.get("REDIS_URL") or not env.get("LOCAL_DATA_DIR"):
        raise RuntimeError("Redis and the persistent data directory are required")
    Path(env["LOCAL_DATA_DIR"]).mkdir(parents=True, exist_ok=True, mode=0o700)
    env["HOSTNAME"] = "0.0.0.0"  # Docker publishes this only on the host's loopback interface.
    env["PORT"] = env.get("PORT", "10000")
    env["NODE_ENV"] = "production"
    return env


if __name__ == "__main__":
    try:
        sys.exit(run(configuration()))
    except Exception as error:
        print(f"Local demo startup failed ({type(error).__name__}); check service logs.", file=sys.stderr)
        sys.exit(1)
