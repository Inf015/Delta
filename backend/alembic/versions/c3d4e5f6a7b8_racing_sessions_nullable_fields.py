"""racing_sessions: make fields nullable, add name, drop unique constraint

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-24 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop unique constraint
    op.drop_constraint('uq_racing_sessions_key', 'racing_sessions', type_='unique')

    # Make fields nullable
    op.alter_column('racing_sessions', 'track', nullable=True)
    op.alter_column('racing_sessions', 'car', nullable=True)
    op.alter_column('racing_sessions', 'simulator', nullable=True)
    op.alter_column('racing_sessions', 'session_date', nullable=True)
    op.alter_column('racing_sessions', 'session_type', nullable=True)

    # Add optional name field
    op.add_column('racing_sessions', sa.Column('name', sa.String(200), nullable=True))


def downgrade() -> None:
    op.drop_column('racing_sessions', 'name')

    op.alter_column('racing_sessions', 'track', nullable=False)
    op.alter_column('racing_sessions', 'car', nullable=False)
    op.alter_column('racing_sessions', 'simulator', nullable=False)
    op.alter_column('racing_sessions', 'session_date', nullable=False)
    op.alter_column('racing_sessions', 'session_type', nullable=False)

    op.create_unique_constraint(
        'uq_racing_sessions_key',
        'racing_sessions',
        ['user_id', 'track', 'car', 'simulator', 'session_date'],
    )
