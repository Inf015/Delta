"""add role to users

Revision ID: k1l2m3n4o5p6
Revises: j0k1l2m3n4o5
Create Date: 2026-04-05
"""
from alembic import op
import sqlalchemy as sa

revision = "k1l2m3n4o5p6"
down_revision = "j0k1l2m3n4o5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TYPE userrole AS ENUM ('pilot', 'technician')")
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.Enum("pilot", "technician", name="userrole"),
            nullable=False,
            server_default="pilot",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "role")
    op.execute("DROP TYPE userrole")
