from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Level, User
from app.schemas import EnvironmentOut
from app.services.environments import environment_snapshot, start_environment, stop_environment

router = APIRouter(prefix="/levels", tags=["environments"])


def _get_level(db: Session, level_id: int) -> Level:
    level = db.get(Level, level_id)
    if level is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "LEVEL_NOT_FOUND", "message": "Nivel no encontrado."},
        )
    return level


@router.post("/{level_id}/environment/start", response_model=EnvironmentOut)
def start_level_environment(
    level_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EnvironmentOut:
    level = _get_level(db, level_id)
    return EnvironmentOut(**start_environment(db, user, level))


@router.get("/{level_id}/environment", response_model=EnvironmentOut)
def get_level_environment(
    level_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EnvironmentOut:
    level = _get_level(db, level_id)
    return EnvironmentOut(**environment_snapshot(db, user, level))


@router.post("/{level_id}/environment/stop", response_model=EnvironmentOut)
def stop_level_environment(
    level_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EnvironmentOut:
    level = _get_level(db, level_id)
    return EnvironmentOut(**stop_environment(db, user, level))
