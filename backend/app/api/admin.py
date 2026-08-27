from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_access_jwt
from app.models import AccessToken, User
from app.schemas import VerifyTokenOut
from app.services.certificate import parse_and_verify_signature

router = APIRouter(prefix="/admin", tags=["admin"])
bearer = HTTPBearer(auto_error=False)


def require_instructor(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
    x_instructor_key: str | None = Header(default=None),
) -> None:
    if x_instructor_key and settings.instructor_key and x_instructor_key == settings.instructor_key:
        return
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHENTICATED", "message": "Se requiere instructor."},
        )
    try:
        payload = decode_access_jwt(creds.credentials)
        user = db.get(User, UUID(str(payload["sub"])))
    except (InvalidTokenError, KeyError, ValueError):
        user = None
    if user is None or not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Se requiere cuenta de instructor."},
        )


@router.get("/verify-token", response_model=VerifyTokenOut)
def verify_token(
    token: str = Query(min_length=8, max_length=200),
    db: Session = Depends(get_db),
    _: None = Depends(require_instructor),
) -> VerifyTokenOut:
    if not parse_and_verify_signature(token):
        return VerifyTokenOut(valid=False)

    record = db.scalar(select(AccessToken).where(AccessToken.token == token))
    if record is None:
        return VerifyTokenOut(valid=False)

    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    expired = expires_at <= datetime.now(timezone.utc)
    owner = db.get(User, record.user_id)
    return VerifyTokenOut(
        valid=not expired,
        full_name=owner.full_name if owner else None,
        student_code=owner.student_code if owner else None,
        email=owner.email if owner else None,
        issued_at=record.issued_at,
        expires_at=record.expires_at,
        expired=expired,
    )
