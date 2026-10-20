import os
import tempfile
from pathlib import Path

TEST_DIR = tempfile.TemporaryDirectory(prefix="medicare-tests-")
os.environ["APP_MODE"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(TEST_DIR.name) / "database.sqlite")
os.environ["LOCAL_DATA_DIR"] = str(Path(TEST_DIR.name) / "private")
os.environ["AUTH_PROVIDER"] = "local"
os.environ["STORAGE_PROVIDER"] = "local"

import pytest  # noqa: E402
from sqlalchemy import event  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.db import engine  # noqa: E402
from app.models import Base  # noqa: E402
from app.main import app  # noqa: E402
from app.jobs import process_report  # noqa: E402


@event.listens_for(engine, "connect")
def foreign_keys(connection, _):
    connection.execute("PRAGMA foreign_keys=ON")


@pytest.fixture(autouse=True)
def database(monkeypatch):
    Base.metadata.create_all(engine)
    monkeypatch.setattr(process_report, "delay", lambda rid, uid: process_report(rid, uid))
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


def register(client, email="one@example.com"):
    result = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "A-long-test-password-123",
            "name": "Synthetic Tester",
            "consent": True,
        },
    )
    assert result.status_code == 201, result.text
    client.headers["X-CSRF-Token"] = client.cookies["medicare_csrf"]
    return result.json()


@pytest.fixture
def signed(client):
    register(client)
    return client
