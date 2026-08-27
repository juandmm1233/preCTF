from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import create_access_jwt, hash_password, verify_password
from app.models import User
from app.schemas import LoginIn, RegisterIn, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=str(user.id),
        email=user.email,
        student_code=user.student_code,
        full_name=user.full_name,
        score=user.score,
        is_admin=user.is_admin,
        created_at=user.created_at,
    )


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterIn, db: Session = Depends(get_db)) -> TokenOut:
    exists = db.scalar(
        select(User).where(
            or_(
                User.email == payload.email.lower(),
                User.student_code == payload.student_code.upper(),
            )
        )
    )
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "ALREADY_REGISTERED",
                "message": "El correo o el código de estudiante ya está registrado.",
            },
        )
    user = User(
        email=payload.email.lower(),
        student_code=payload.student_code.upper(),
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenOut(access_token=create_access_jwt(str(user.id), user.is_admin))


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    identifier = payload.identifier.strip()
    user = db.scalar(
        select(User).where(
            or_(
                User.email == identifier.lower(),
                User.student_code == identifier.upper(),
            )
        )
    )
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_CREDENTIALS",
                "message": "Identificador o contraseña incorrectos.",
            },
        )
    return TokenOut(access_token=create_access_jwt(str(user.id), user.is_admin))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return _user_out(user)
