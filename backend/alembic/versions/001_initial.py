"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-08-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("student_code", sa.String(32), nullable=False, unique=True),
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_student_code", "users", ["student_code"])

    op.create_table(
        "levels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_index", sa.Integer(), nullable=False, unique=True),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("vector_name", sa.String(80), nullable=False),
        sa.Column("lab_endpoint", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("flag_hash", sa.String(64), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("hint_cost", sa.Integer(), nullable=False),
        sa.Column("hint_text", sa.Text(), nullable=False),
        sa.Column("is_bonus", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "honeypots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("label", sa.String(80), nullable=False),
        sa.Column("flag_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("penalty", sa.Integer(), nullable=False, server_default="50"),
    )

    op.create_table(
        "progress",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("level_id", sa.Integer(), sa.ForeignKey("levels.id"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("points_awarded", sa.Integer(), nullable=False),
        sa.UniqueConstraint("user_id", "level_id", name="uq_progress_user_level"),
    )
    op.create_index("ix_progress_user_id", "progress", ["user_id"])
    op.create_index("ix_progress_level_id", "progress", ["level_id"])

    op.create_table(
        "submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("level_id", sa.Integer(), sa.ForeignKey("levels.id"), nullable=False),
        sa.Column("result", sa.String(32), nullable=False),
        sa.Column("points_delta", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ip", sa.String(64), nullable=False, server_default=""),
    )
    op.create_index("ix_submissions_user_id", "submissions", ["user_id"])
    op.create_index("ix_submissions_level_id", "submissions", ["level_id"])

    op.create_table(
        "hint_uses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("level_id", sa.Integer(), sa.ForeignKey("levels.id"), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "level_id", name="uq_hint_user_level"),
    )
    op.create_index("ix_hint_uses_user_id", "hint_uses", ["user_id"])
    op.create_index("ix_hint_uses_level_id", "hint_uses", ["level_id"])

    op.create_table(
        "access_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("token", sa.String(160), nullable=False, unique=True),
        sa.Column("hmac_signature", sa.String(64), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("access_tokens")
    op.drop_table("hint_uses")
    op.drop_table("submissions")
    op.drop_table("progress")
    op.drop_table("honeypots")
    op.drop_table("levels")
    op.drop_table("users")
