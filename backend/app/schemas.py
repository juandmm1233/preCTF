from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class RegisterIn(BaseModel):
    email: str = Field(min_length=5, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    student_code: str = Field(min_length=4, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    identifier: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    email: str
    student_code: str
    full_name: str
    score: int
    is_admin: bool
    created_at: datetime


class SubmitFlagIn(BaseModel):
    flag: str = Field(min_length=1, max_length=256)


class SubmitFlagOut(BaseModel):
    ok: bool
    result: Literal["correct", "incorrect", "honeypot", "already_completed"]
    points: int
    points_delta: int
    unlocked_next: bool
    message: str
    token: str | None = None


class HintOut(BaseModel):
    hint: str
    already_used: bool
    points_delta: int
    score: int


class EnvironmentOut(BaseModel):
    status: Literal["idle", "starting", "running", "stopping", "stopped", "error"]
    public_url: str | None = None
    expires_at: datetime | None = None
    has_lab: bool = False
    message: str | None = None


class LevelCardOut(BaseModel):
    id: int
    order_index: int
    slug: str
    title: str
    vector_name: str
    lab_endpoint: str
    description: str
    points: int
    hint_cost: int
    is_bonus: bool
    status: Literal["locked", "available", "completed"]
    hint_used: bool
    completed_at: datetime | None = None


class LevelDetailOut(LevelCardOut):
    tutorial_content: str
    environment: EnvironmentOut


class DashboardOut(BaseModel):
    user: UserOut
    completed: int
    total: int
    levels: list[LevelCardOut]
    access_token: str | None = None
    token_expires_at: datetime | None = None


class VerifyTokenOut(BaseModel):
    valid: bool
    full_name: str | None = None
    student_code: str | None = None
    email: str | None = None
    issued_at: datetime | None = None
    expires_at: datetime | None = None
    expired: bool = False
