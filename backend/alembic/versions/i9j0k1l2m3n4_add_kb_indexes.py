"""add composite indexes for knowledge_profiles and recommendations

Revision ID: i9j0k1l2m3n4
Revises: h8i9j0k1l2m3
Create Date: 2026-04-05
"""
from alembic import op

revision = "i9j0k1l2m3n4"
down_revision = "h8i9j0k1l2m3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # get_or_create_profile filtra por estos 4 campos
    op.create_index(
        "ix_knowledge_profiles_lookup",
        "knowledge_profiles",
        ["user_id", "track", "car", "simulator"],
        unique=True,
    )
    # update_after_ai filtra recomendaciones pendientes por perfil
    op.create_index(
        "ix_recommendations_profile_tested",
        "recommendations",
        ["profile_id", "tested"],
    )


def downgrade() -> None:
    op.drop_index("ix_recommendations_profile_tested", table_name="recommendations")
    op.drop_index("ix_knowledge_profiles_lookup", table_name="knowledge_profiles")
