"""Exercise the Render image behind verified local HTTPS with disposable resources.

Requires medicare-ai-render-demo:local, the development Compose database/network,
and loopback port 3002. Creates/removes its own PostgreSQL DB/role, Redis, volume,
container and local TLS certificate. Never uses a patient database.
"""
import http.server
import json
import os
from pathlib import Path
import secrets
import ssl
import subprocess
import tempfile
import threading
import time
import uuid

import httpx
import psycopg
from psycopg import sql


def docker(*args, env=None):
    result = subprocess.run(
        ["docker", *args], env=env, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


class Proxy(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def proxy(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", "0"))) or None
        headers = {
            k: v for k, v in self.headers.items()
            if k.lower() not in {"host", "connection", "transfer-encoding", "content-length"}
        }
        with httpx.Client(trust_env=False, timeout=40) as client:
            try:
                result = client.request(
                    self.command, "http://127.0.0.1:3002" + self.path,
                    headers=headers, content=body,
                )
            except httpx.HTTPError:
                self.send_error(503, "Demo is starting")
                return
        self.send_response(result.status_code)
        for key, value in result.headers.multi_items():
            if key.lower() not in {
                "content-length", "connection", "transfer-encoding", "content-encoding"
            }:
                self.send_header(key, value)
        self.send_header("Content-Length", str(len(result.content)))
        self.end_headers()
        self.wfile.write(result.content)

    do_GET = do_POST = do_PATCH = do_DELETE = proxy


def main():
    suffix = uuid.uuid4().hex[:10]
    name = f"medicare-render-check-{suffix}"
    queue, volume = name + "-queue", name + "-data"
    role = database = "render_check_" + suffix
    containers = []
    created_db = created_role = created_volume = False
    server = None
    admin = psycopg.connect(
        "postgresql://medicare:local-development-only@127.0.0.1:5432/medicare",
        autocommit=True,
    )
    try:
        password = secrets.token_hex(24)
        admin.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOBYPASSRLS").format(
            sql.Identifier(role), sql.Literal(password),
        ))
        created_role = True
        admin.execute(sql.SQL("CREATE DATABASE {} OWNER {}").format(
            sql.Identifier(database), sql.Identifier(role),
        ))
        created_db = True
        with tempfile.TemporaryDirectory(prefix="medicare-render-tls-") as directory:
            cert, key = (Path(directory) / filename for filename in ["cert.pem", "key.pem"])
            subprocess.run([
                "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                "-keyout", str(key), "-out", str(cert), "-days", "1",
                "-subj", "/CN=localhost",
                "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1",
            ], check=True, capture_output=True)
            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Proxy)
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(cert, key)
            server.socket = context.wrap_socket(server.socket, server_side=True)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            origin = f"https://127.0.0.1:{server.server_port}"
            trust = ssl.create_default_context(cafile=str(cert))
            docker("volume", "create", volume)
            created_volume = True
            docker("run", "-d", "--name", queue, "--network", "medicare-ai_default",
                   "redis:7-alpine", "redis-server", "--maxmemory-policy", "noeviction")
            containers.append(queue)
            env = os.environ.copy()
            env.update(
                APP_MODE="demo",
                APP_SECRET=secrets.token_hex(32),
                DATABASE_URL=f"postgresql://{role}:{password}@postgres:5432/{database}",
                REDIS_URL=f"redis://{queue}:6379/0",
                RENDER_EXTERNAL_URL=origin,
                LOCAL_DATA_DIR="/var/data/medicare",
                RETENTION_DAYS="1",
            )
            options = []
            for variable in (
                "APP_MODE", "APP_SECRET", "DATABASE_URL", "REDIS_URL",
                "RENDER_EXTERNAL_URL", "LOCAL_DATA_DIR", "RETENTION_DAYS",
            ):
                options.extend(["-e", variable])
            docker("run", "-d", "--name", name, "--network", "medicare-ai_default",
                   "-p", "127.0.0.1:3002:10000", "-v", f"{volume}:/var/data",
                   *options, "medicare-ai-render-demo:local", env=env)
            containers.append(name)

            def ready():
                for _ in range(90):
                    try:
                        response = httpx.get(
                            origin + "/api/v1/health", verify=trust, timeout=2, trust_env=False
                        )
                        if response.status_code == 200:
                            assert response.json()["mode"] == "demo"
                            return
                    except httpx.HTTPError:
                        pass
                    time.sleep(0.5)
                raise RuntimeError("Render image failed readiness")

            ready()
            assert docker("exec", name, "id", "-u") == "10001"
            with httpx.Client(base_url=origin, verify=trust, trust_env=False, timeout=40) as client:
                assert "Interactive demo" in client.get("/").text
                sample = client.get("/demo/sample-report.pdf").content
                assert sample.startswith(b"%PDF")
                assert client.get("/demo/sample-prescription.png").content.startswith(b"\x89PNG")
                result = client.post("/api/v1/auth/register", json={
                    "email": f"restart-{suffix}@example.com",
                    "password": "Synthetic-demo-restart-123!",
                    "name": "Synthetic Restart Tester", "consent": True,
                }, headers={"Origin": origin})
                assert result.status_code == 201, result.status_code
                cookies = result.headers.get_list("set-cookie")
                assert all("Secure" in cookie and "SameSite=lax" in cookie for cookie in cookies)
                assert any("medicare_session=" in cookie and "HttpOnly" in cookie for cookie in cookies)
                headers = {"Origin": origin, "X-CSRF-Token": client.cookies["medicare_csrf"]}
                try:
                    result = client.post(
                        "/api/v1/reports/upload", headers=headers,
                        files={"file": ("synthetic-demo.pdf", sample, "application/pdf")},
                        data={"consent": "true", "report_type": "heart_rate"},
                    )
                    assert result.status_code == 201, result.status_code
                    report = result.json()["id"]
                    for _ in range(60):
                        if client.get(f"/api/v1/reports/{report}").json()["status"] == "completed":
                            break
                        time.sleep(0.5)
                    result = client.get(f"/api/v1/reports/{report}/analysis").json()
                    assert result["measurements"][0]["value"] == 88
                    docker("restart", "--time", "25", name)
                    ready()
                    assert client.get("/api/v1/users/me").status_code == 200
                    assert client.get(f"/api/v1/reports/{report}/download").content == sample
                    print("PASS: verified HTTPS, secure cookies, non-root full stack, OCR, restart persistence")
                finally:
                    result = client.request(
                        "DELETE", "/api/v1/users/me", headers=headers,
                        json={"confirmation": "DELETE MY ACCOUNT"},
                    )
                    assert result.status_code == 204, result.status_code

            # Exercise the existing ownership/CSRF/PDF/image OCR suite over verified HTTPS.
            os.environ["MEDICARE_API_BASE"] = origin + "/api/v1"
            os.environ["SSL_CERT_FILE"] = str(cert)
            import smoke
            smoke.BASE = os.environ["MEDICARE_API_BASE"]
            smoke.main()
            # Killing the worker must terminate the container, not leave a healthy-looking UI.
            docker("exec", name, "/app/services/api/.venv/bin/python", "-c", """
import os,signal
from pathlib import Path
for entry in Path('/proc').iterdir():
    if not entry.name.isdigit() or int(entry.name)==os.getpid():
        continue
    try:
        argv=(entry/'cmdline').read_bytes().split(b'\\0')
        if b'worker' in argv and any(b'celery' in arg for arg in argv):
            os.kill(int(entry.name), signal.SIGTERM)
            break
    except (FileNotFoundError, PermissionError):
        pass
""")
            for _ in range(60):
                state = json.loads(docker("inspect", "--format", "{{json .State}}", name))
                if not state["Running"]:
                    assert state["ExitCode"] != 0
                    print("PASS: worker failure stops the full service for platform restart")
                    break
                time.sleep(0.5)
            else:
                raise RuntimeError("Worker failure did not stop the container")
    except Exception:
        diagnostics = []
        for container in containers:
            result = subprocess.run(
                ["docker", "logs", "--tail", "100", container], capture_output=True, text=True
            )
            diagnostics.append(container + "\n" + result.stdout + result.stderr)
        Path("/tmp/medicare-render-smoke-failure.log").write_text("\n".join(diagnostics))
        raise
    finally:
        if server:
            server.shutdown()
            server.server_close()
        for container in reversed(containers):
            subprocess.run(["docker", "rm", "-f", container], capture_output=True, check=False)
        if created_volume:
            subprocess.run(["docker", "volume", "rm", volume], capture_output=True, check=False)
        if created_db:
            admin.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=%s",
                (database,),
            )
            admin.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(database)))
        if created_role:
            admin.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(role)))
        admin.close()


if __name__ == "__main__":
    main()
