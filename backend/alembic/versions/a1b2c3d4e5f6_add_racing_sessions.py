"""add racing_sessions table and update fks

Revision ID: a1b2c3d4e5f6
Revises: bcfff7642208
Create Date: 2026-03-19 15:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'bcfff7642208'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Usar SQL puro para evitar conflictos con ENUMs existentes
    op.execute("""
        CREATE TABLE racing_sessions (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id),
            track VARCHAR(200) NOT NULL,
            car VARCHAR(200) NOT NULL,
            simulator simulator NOT NULL,
            session_date VARCHAR(30) NOT NULL,
            session_type sessiontype NOT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            CONSTRAINT uq_racing_sessions_key UNIQUE (user_id, track, car, simulator, session_date)
        )
    """)
    op.create_index('ix_racing_sessions_user_id', 'racing_sessions', ['user_id'], unique=False)

    # Añadir racing_session_id a telemetry_sessions
    op.add_column(
        'telemetry_sessions',
        sa.Column('racing_session_id', sa.UUID(), nullable=True)
    )
    op.create_foreign_key(
        'fk_telemetry_sessions_racing_session_id',
        'telemetry_sessions', 'racing_sessions',
        ['racing_session_id'], ['id']
    )
    op.create_index(
        'ix_telemetry_sessions_racing_session_id',
        'telemetry_sessions', ['racing_session_id'], unique=False
    )

    # Hacer session_id nullable en analyses
    op.drop_index('ix_analyses_session_id', table_name='analyses')
    op.alter_column('analyses', 'session_id', nullable=True)
    # Partial unique index: solo cuando session_id no es null
    op.execute(
        "CREATE UNIQUE INDEX ix_analyses_session_id ON analyses (session_id) WHERE session_id IS NOT NULL"
    )

    # Añadir racing_session_id a analyses
    op.add_column(
        'analyses',
        sa.Column('racing_session_id', sa.UUID(), nullable=True)
    )
    op.create_foreign_key(
        'fk_analyses_racing_session_id',
        'analyses', 'racing_sessions',
        ['racing_session_id'], ['id']
    )
    op.create_index(
        'ix_analyses_racing_session_id',
        'analyses', ['racing_session_id'], unique=False
    )


def downgrade() -> None:
    op.drop_index('ix_analyses_racing_session_id', table_name='analyses')
    op.drop_constraint('fk_analyses_racing_session_id', 'analyses', type_='foreignkey')
    op.drop_column('analyses', 'racing_session_id')

    op.drop_index('ix_analyses_session_id', table_name='analyses')
    op.alter_column('analyses', 'session_id', nullable=False)
    op.create_index('ix_analyses_session_id', 'analyses', ['session_id'], unique=True)

    op.drop_index('ix_telemetry_sessions_racing_session_id', table_name='telemetry_sessions')
    op.drop_constraint('fk_telemetry_sessions_racing_session_id', 'telemetry_sessions', type_='foreignkey')
    op.drop_column('telemetry_sessions', 'racing_session_id')

    op.drop_index('ix_racing_sessions_user_id', table_name='racing_sessions')
    op.drop_table('racing_sessions')
