"""Run the single-instance Render demo with supervised child processes.

Render terminates HTTPS. Only Next.js binds the public port; FastAPI is loopback.
The API, worker, and scheduler share one encrypted persistent disk.
"""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "services" / "api"
BIN = API / ".venv" / "bin"


def configuration():
    env = os.environ.copy()
    if env.get("APP_MODE") != "demo":
        raise RuntimeError("This entrypoint is only for APP_MODE=demo")
    origin = env.get("ALLOWED_ORIGINS") or env.get("RENDER_EXTERNAL_URL", "").rstrip("/")
    if not origin:
        raise RuntimeError("RENDER_EXTERNAL_URL or ALLOWED_ORIGINS is required")
    env["ALLOWED_ORIGINS"] = origin
    database = env.get("DATABASE_URL", "")
    for prefix in ("postgres://", "postgresql://"):
        if database.startswith(prefix):
            database = "postgresql+psycopg://" + database[len(prefix):]
            break
    if not database:
        raise RuntimeError("DATABASE_URL is required")
    env["DATABASE_URL"] = database
    if not env.get("REDIS_URL"):
        raise RuntimeError("REDIS_URL is required")
    env["HOSTNAME"] = "0.0.0.0"
    env["PORT"] = env.get("PORT", "10000")
    env["NODE_ENV"] = "production"
    return env


def main():
    env = configuration()
    children = []
    stopping = False

    def stop(_signal, _frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    def launch(name, command, cwd=API):
        process = subprocess.Popen(command, cwd=cwd, env=env, start_new_session=True)
        children.append((name, process))
        return process

    try:
        migration = launch("migration", [str(BIN / "alembic"), "upgrade", "head"])
        deadline = time.monotonic() + 120
        while migration.poll() is None:
            if stopping or time.monotonic() > deadline:
                raise RuntimeError("Migration interrupted or timed out")
            time.sleep(0.2)
        if migration.returncode:
            raise RuntimeError("Database migration failed")
        children.remove(("migration", migration))
        launch("api", [
            str(BIN / "uvicorn"), "app.main:app", "--host", "127.0.0.1",
            "--port", "8000", "--no-access-log",
        ])
        launch("worker", [
            str(BIN / "celery"), "-A", "app.jobs:celery", "worker",
            "--loglevel=WARNING", "--concurrency=1", "--hostname=demo@%h",
        ])
        data = Path(env["LOCAL_DATA_DIR"])
        launch("scheduler", [
            str(BIN / "celery"), "-A", "app.jobs:celery", "beat",
            "--loglevel=WARNING", "--schedule", str(data / "beat-schedule"), "--pidfile=",
        ])
        deadline = time.monotonic() + 90
        while not stopping:
            if any(child.poll() is not None for _, child in children):
                raise RuntimeError("A demo service exited during startup")
            try:
                with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=2) as response:
                    if response.status == 200:
                        break
            except OSError:
                pass
            if time.monotonic() > deadline:
                raise RuntimeError("API readiness timed out")
            time.sleep(0.5)
        if stopping:
            return 0
        launch("web", ["node", str(ROOT / "web/apps/web/server.js")], ROOT / "web")
        print("Demo services started; clinical inference remains unavailable.", flush=True)
        while not stopping:
            for name, child in children:
                if child.poll() is not None:
                    raise RuntimeError(f"Demo service exited: {name}")
            time.sleep(0.5)
        return 0
    finally:
        for _, child in reversed(children):
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
        deadline = time.monotonic() + 20
        for _, child in reversed(children):
            try:
                child.wait(timeout=max(0.1, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        # Configuration/connection strings can contain credentials. Do not dump exceptions.
        print(f"Demo startup failed ({type(error).__name__}); check service readiness.", file=sys.stderr)
        sys.exit(1)
