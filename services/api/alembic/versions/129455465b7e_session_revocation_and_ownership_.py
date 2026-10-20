"""Session revocation and database ownership policies."""

from alembic import op
import sqlalchemy as sa

revision = "129455465b7e"
down_revision = "4f4076645883"
branch_labels = None
depends_on = None
TABLES = [
    "profiles",
    "consent_records",
    "medical_reports",
    "report_extractions",
    "ai_analysis_results",
    "prescriptions",
    "prescription_items",
    "report_access_logs",
    "audit_events",
]


def upgrade():
    op.add_column("users", sa.Column("session_version", sa.Integer(), nullable=False, server_default="0"))
    if op.get_bind().dialect.name == "postgresql":
        for table in TABLES:
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
            op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
            op.execute(
                f"CREATE POLICY owner_isolation ON {table} USING (owner_id = NULLIF(current_setting('app.user_id', true), '')::uuid) WITH CHECK (owner_id = NULLIF(current_setting('app.user_id', true), '')::uuid)"
            )


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        for table in TABLES:
            op.execute(f"DROP POLICY owner_isolation ON {table}")
            op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
            op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
    op.drop_column("users", "session_version")
