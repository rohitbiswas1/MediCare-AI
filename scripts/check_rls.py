"""Verify PostgreSQL owner isolation with an actual non-superuser role and synthetic records."""

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services/api"))
from datetime import timedelta

from app.db import engine
from app.models import MedicalReport, User, now
from sqlalchemy import text
from sqlalchemy.orm import Session

role = "medicare_rls_check_" + uuid.uuid4().hex[:12]
users = [uuid.uuid4(), uuid.uuid4()]
try:
    with engine.begin() as conn:
        conn.execute(text(f"CREATE ROLE {role} NOLOGIN NOSUPERUSER NOBYPASSRLS"))
        conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
        conn.execute(text(f"GRANT SELECT ON medical_reports TO {role}"))
        with Session(bind=conn) as db:
            for uid in users:
                db.add(User(id=uid, email=f"rls-{uid}@example.com", auth_provider="local"))
            db.flush()
            for uid in users:
                db.add(
                    MedicalReport(
                        owner_id=uid,
                        filename="synthetic-rls.pdf",
                        storage_key=f"rls-check/{uid}",
                        content_type="application/pdf",
                        size_bytes=1,
                        sha256="0" * 64,
                        safety_scan="test_only",
                        expires_at=now() + timedelta(hours=1),
                    )
                )
            db.flush()
        conn.execute(text(f"SET LOCAL ROLE {role}"))
        conn.execute(text("SELECT set_config('app.user_id', :owner, true)"), {"owner": str(users[0])})
        rows = conn.execute(text("SELECT owner_id FROM medical_reports")).all()
        assert len(rows) == 1 and str(rows[0][0]) == str(users[0]), rows
        conn.execute(text("SELECT set_config('app.user_id', '', true)"))
        assert conn.execute(text("SELECT COUNT(*) FROM medical_reports")).scalar() == 0
        conn.execute(text("RESET ROLE"))
    print("PASS: forced PostgreSQL row-level security hides other users and denies absent context")
finally:
    with engine.begin() as conn:
        for uid in users:
            conn.execute(text("DELETE FROM users WHERE id=:id"), {"id": uid})
        conn.execute(text(f"DROP OWNED BY {role}"))
        conn.execute(text(f"DROP ROLE IF EXISTS {role}"))
