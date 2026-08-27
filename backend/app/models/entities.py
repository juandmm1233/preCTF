import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    student_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    score: Mapped[int] = mapped_column(Integer, default=0)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    progress: Mapped[list["Progress"]] = relationship(back_populates="user")
    submissions: Mapped[list["Submission"]] = relationship(back_populates="user")
    hint_uses: Mapped[list["HintUse"]] = relationship(back_populates="user")
    access_token: Mapped["AccessToken | None"] = relationship(back_populates="user", uselist=False)
    lab_sessions: Mapped[list["LabSession"]] = relationship(back_populates="user")


class Level(Base):
    __tablename__ = "levels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_index: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    title: Mapped[str] = mapped_column(String(120))
    vector_name: Mapped[str] = mapped_column(String(80))
    lab_endpoint: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)
    flag_hash: Mapped[str] = mapped_column(String(64))
    points: Mapped[int] = mapped_column(Integer)
    hint_cost: Mapped[int] = mapped_column(Integer)
    hint_text: Mapped[str] = mapped_column(Text)
    is_bonus: Mapped[bool] = mapped_column(Boolean, default=False)
    tutorial_content: Mapped[str] = mapped_column(Text, default="")


class Progress(Base):
    __tablename__ = "progress"
    __table_args__ = (UniqueConstraint("user_id", "level_id", name="uq_progress_user_level"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    level_id: Mapped[int] = mapped_column(Integer, ForeignKey("levels.id"), index=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    points_awarded: Mapped[int] = mapped_column(Integer)

    user: Mapped[User] = relationship(back_populates="progress")
    level: Mapped[Level] = relationship()


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    level_id: Mapped[int] = mapped_column(Integer, ForeignKey("levels.id"), index=True)
    result: Mapped[str] = mapped_column(String(32))
    points_delta: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ip: Mapped[str] = mapped_column(String(64), default="")

    user: Mapped[User] = relationship(back_populates="submissions")


class HintUse(Base):
    __tablename__ = "hint_uses"
    __table_args__ = (UniqueConstraint("user_id", "level_id", name="uq_hint_user_level"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    level_id: Mapped[int] = mapped_column(Integer, ForeignKey("levels.id"), index=True)
    used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="hint_uses")


class AccessToken(Base):
    __tablename__ = "access_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, index=True)
    token: Mapped[str] = mapped_column(String(160), unique=True)
    hmac_signature: Mapped[str] = mapped_column(String(64))
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="access_token")


class LabSession(Base):
    __tablename__ = "lab_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    level_id: Mapped[int] = mapped_column(Integer, ForeignKey("levels.id"), index=True)
    container_id: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(24), default="idle")
    public_url: Mapped[str] = mapped_column(String(255), default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="lab_sessions")
    level: Mapped[Level] = relationship()


class Honeypot(Base):
    __tablename__ = "honeypots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    label: Mapped[str] = mapped_column(String(80))
    flag_hash: Mapped[str] = mapped_column(String(64), unique=True)
    penalty: Mapped[int] = mapped_column(Integer, default=50)
