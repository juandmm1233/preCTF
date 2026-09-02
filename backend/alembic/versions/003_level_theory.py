"""level theory fields

Revision ID: 003_level_theory
Revises: 002_tutorials_and_lab_sessions
Create Date: 2026-09-01
"""

from alembic import op
import sqlalchemy as sa

revision = "003_level_theory"
down_revision = "002_tutorials_and_lab_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "levels",
        sa.Column("explanation", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "levels",
        sa.Column("goal", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "levels",
        sa.Column("tutorial_url", sa.String(512), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("levels", "tutorial_url")
    op.drop_column("levels", "goal")
    op.drop_column("levels", "explanation")
