from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Level, User
from app.schemas import HintOut, SubmitFlagIn, SubmitFlagOut
from app.services.progression import submit_flag, use_hint
from app.services.rate_limit import check_submit_rate

router = APIRouter(prefix="/levels", tags=["levels"])


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
