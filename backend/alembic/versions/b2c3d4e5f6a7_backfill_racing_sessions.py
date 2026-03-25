"""backfill racing_sessions from existing telemetry_sessions

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-19 15:05:00.000000

"""
from typing import Sequence, Union
from alembic import op


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Crear RacingSessions para todas las telemetry_sessions existentes agrupadas por clave única
    op.execute("""
        INSERT INTO racing_sessions (id, user_id, track, car, simulator, session_date, session_type, created_at)
        SELECT
            gen_random_uuid(),
            user_id,
            track,
            car,
            simulator,
            session_date,
            MIN(session_type) AS session_type,
            MIN(created_at) AS created_at
        FROM telemetry_sessions
        WHERE racing_session_id IS NULL
        GROUP BY user_id, track, car, simulator, session_date
        ON CONFLICT ON CONSTRAINT uq_racing_sessions_key DO NOTHING
    """)

    # Actualizar telemetry_sessions con el racing_session_id correspondiente
    op.execute("""
        UPDATE telemetry_sessions ts
        SET racing_session_id = rs.id
        FROM racing_sessions rs
        WHERE ts.user_id = rs.user_id
          AND ts.track = rs.track
          AND ts.car = rs.car
          AND ts.simulator = rs.simulator
          AND ts.session_date = rs.session_date
          AND ts.racing_session_id IS NULL
    """)


def downgrade() -> None:
    # El downgrade de backfill simplemente limpia los FKs
    op.execute("UPDATE telemetry_sessions SET racing_session_id = NULL")
