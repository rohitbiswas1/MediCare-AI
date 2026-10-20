"""Retain catalog-backed, unconfirmed prescription extraction candidates."""

from alembic import op
import sqlalchemy as sa

revision = "8a0e7dcb63e2"
down_revision = "6cfd98e23b11"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "report_extractions",
        sa.Column("prescription_candidates", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade():
    op.drop_column("report_extractions", "prescription_candidates")
