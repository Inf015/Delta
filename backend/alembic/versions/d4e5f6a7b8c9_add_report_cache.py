"""add report_cache to racing_sessions

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-03-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = 'd4e5f6a7b8c9'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('racing_sessions', sa.Column('report_cache', JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column('racing_sessions', 'report_cache')
