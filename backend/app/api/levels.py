from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Level, Progress, User
from app.schemas import EnvironmentOut, HintOut, LevelDetailOut, SubmitFlagIn, SubmitFlagOut
from app.services.environments import environment_snapshot
from app.services.progression import (
    completed_level_ids,
    hinted_level_ids,
    is_level_unlocked,
    submit_flag,
    use_hint,
)
from app.services.rate_limit import check_submit_rate

router = APIRouter(prefix="/levels", tags=["levels"])


def _get_level(db: Session, level_id: int) -> Level:
    level = db.get(Level, level_id)
    if level is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "LEVEL_NOT_FOUND", "message": "Nivel no encontrado."},
        )
    return level


@router.get("/{level_id}", response_model=LevelDetailOut)
def get_level(
    level_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> LevelDetailOut:
    level = _get_level(db, level_id)
    if not is_level_unlocked(db, user, level):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "LEVEL_LOCKED", "message": "Completa el nivel anterior primero."},
        )
    done = completed_level_ids(db, user)
    hinted = hinted_level_ids(db, user)
    completed_at = None
    if level.id in done:
        card_status = "completed"
        row = db.scalar(
            select(Progress).where(Progress.user_id == user.id, Progress.level_id == level.id)
        )
        completed_at = row.completed_at if row else None
    else:
        card_status = "available"
    return LevelDetailOut(
        id=level.id,
        order_index=level.order_index,
        slug=level.slug,
        title=level.title,
        vector_name=level.vector_name,
        lab_endpoint=level.lab_endpoint,
        description=level.description,
        points=level.points,
        hint_cost=level.hint_cost,
        is_bonus=level.is_bonus,
        status=card_status,
        hint_used=level.id in hinted,
        completed_at=completed_at,
        tutorial_content=level.tutorial_content or "",
        environment=EnvironmentOut(**environment_snapshot(db, user, level)),
    )


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    if request.client:
        return request.client.host
    return ""


@router.post("/{level_id}/submit", response_model=SubmitFlagOut)
def submit_level_flag(
    level_id: int,
    payload: SubmitFlagIn,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SubmitFlagOut:
    check_submit_rate(str(user.id))
    level = db.get(Level, level_id)
    if level is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "LEVEL_NOT_FOUND", "message": "Nivel no encontrado."},
        )
    result = submit_flag(db, user, level, payload.flag, _client_ip(request))
    return SubmitFlagOut(**result)


@router.post("/{level_id}/hint", response_model=HintOut)
def reveal_hint(
    level_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HintOut:
    level = db.get(Level, level_id)
    if level is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "LEVEL_NOT_FOUND", "message": "Nivel no encontrado."},
        )
    return HintOut(**use_hint(db, user, level))
