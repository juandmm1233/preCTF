"""tutorials and lab sessions

Revision ID: 002_tutorials_and_lab_sessions
Revises: 001_initial
Create Date: 2026-08-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002_tutorials_and_lab_sessions"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "levels",
        sa.Column("tutorial_content", sa.Text(), nullable=False, server_default=""),
    )

    op.create_table(
        "lab_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("level_id", sa.Integer(), sa.ForeignKey("levels.id"), nullable=False),
        sa.Column("container_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("public_url", sa.String(255), nullable=False, server_default=""),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_lab_sessions_user_id", "lab_sessions", ["user_id"])
    op.create_index("ix_lab_sessions_level_id", "lab_sessions", ["level_id"])
    op.create_index(
        "uq_lab_sessions_active_user_level",
        "lab_sessions",
        ["user_id", "level_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('starting', 'running')"),
    )


def downgrade() -> None:
    op.drop_index("uq_lab_sessions_active_user_level", table_name="lab_sessions")
    op.drop_index("ix_lab_sessions_level_id", table_name="lab_sessions")
    op.drop_index("ix_lab_sessions_user_id", table_name="lab_sessions")
    op.drop_table("lab_sessions")
    op.drop_column("levels", "tutorial_content")
