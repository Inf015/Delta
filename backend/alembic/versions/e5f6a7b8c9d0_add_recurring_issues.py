"""add recurring_issues to knowledge_profiles

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-03-24
"""
from alembic import op
import sqlalchemy as sa

revision = 'e5f6a7b8c9d0'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('knowledge_profiles', sa.Column('recurring_issues', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('knowledge_profiles', 'recurring_issues')
