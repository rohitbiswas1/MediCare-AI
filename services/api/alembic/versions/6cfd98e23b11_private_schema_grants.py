"""Prevent direct Supabase browser roles from reading application tables."""

from alembic import op

revision = "6cfd98e23b11"
down_revision = "129455465b7e"
branch_labels = None
depends_on = None
TABLES = [
    "users",
    "profiles",
    "consent_records",
    "medical_reports",
    "report_extractions",
    "ai_analysis_results",
    "model_versions",
    "prescriptions",
    "prescription_items",
    "medicines",
    "pharmacies",
    "pharmacy_inventory",
    "report_access_logs",
    "audit_events",
]


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in TABLES:
        op.execute(f"REVOKE ALL ON TABLE {table} FROM PUBLIC")
        for role in ["anon", "authenticated"]:
            op.execute(
                f"DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='{role}') THEN EXECUTE 'REVOKE ALL ON TABLE {table} FROM {role}'; END IF; END $$"
            )


def downgrade():
    # Do not silently restore access to private healthcare tables on rollback.
    pass
