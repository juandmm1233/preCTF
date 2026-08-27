from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_jwt
from app.models import User

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={
            "code": "UNAUTHENTICATED",
            "message": "Inicia sesión para continuar.",
        })
    try:
        payload = decode_access_jwt(creds.credentials)
        user_id = UUID(payload["sub"])
    except (InvalidTokenError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={
            "code": "INVALID_TOKEN",
            "message": "Sesión inválida o expirada.",
        })
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={
            "code": "UNAUTHENTICATED",
            "message": "Usuario no encontrado.",
        })
    return user


def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={
            "code": "FORBIDDEN",
            "message": "Se requiere cuenta de instructor.",
        })
    return user
