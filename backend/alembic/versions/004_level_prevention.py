"""level prevention field

Revision ID: 004_level_prevention
Revises: 003_level_theory
Create Date: 2026-09-01
"""

from alembic import op
import sqlalchemy as sa

revision = "004_level_prevention"
down_revision = "003_level_theory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "levels",
        sa.Column("prevention", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("levels", "prevention")
