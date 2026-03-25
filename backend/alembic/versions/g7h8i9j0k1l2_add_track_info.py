"""add track_info table

Revision ID: g7h8i9j0k1l2
Revises: f6a7b8c9d0e1
Create Date: 2026-03-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = 'g7h8i9j0k1l2'
down_revision = 'f6a7b8c9d0e1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'track_info',
        sa.Column('track_id', sa.String(200), primary_key=True),
        sa.Column('display_name', sa.String(200), nullable=True),
        sa.Column('country', sa.String(100), nullable=True),
        sa.Column('track_type', sa.String(20), nullable=False, server_default='unknown'),
        sa.Column('length_m', sa.Float, nullable=True),
        sa.Column('turns', sa.Integer, nullable=True),
        sa.Column('characteristics', JSONB, nullable=True),
        sa.Column('sectors', JSONB, nullable=True),
        sa.Column('key_corners', JSONB, nullable=True),
        sa.Column('lap_record', JSONB, nullable=True),
        sa.Column('notes', sa.String(1000), nullable=True),
        sa.Column('map_path', sa.String(500), nullable=True),
        sa.Column('source', sa.String(20), nullable=False, server_default='unknown'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('track_info')
