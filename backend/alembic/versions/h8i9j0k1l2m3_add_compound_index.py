"""add compound index racing_session_id+processed

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
Create Date: 2026-03-25
"""
from alembic import op

revision = "h8i9j0k1l2m3"
down_revision = "g7h8i9j0k1l2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_telemetry_sessions_racing_session_processed",
        "telemetry_sessions",
        ["racing_session_id", "processed"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_telemetry_sessions_racing_session_processed",
        table_name="telemetry_sessions",
    )
