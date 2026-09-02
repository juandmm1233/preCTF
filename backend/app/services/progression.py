from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import flags_match, hash_flag
from app.models import AccessToken, HintUse, Honeypot, Level, Progress, Submission, User
from app.services.certificate import issue_access_token

HONEYPOT_PUBLIC_RESULT = "honeypot"
TEST_UNLOCK_ALL_EMAIL = "juan.martinezmoral@campusucc.edu.co"


def _skips_sequential_lock(user: User) -> bool:
    return (user.email or "").lower() == TEST_UNLOCK_ALL_EMAIL


def _required_levels(db: Session) -> list[Level]:
    return list(
        db.scalars(
            select(Level).where(Level.is_bonus.is_(False)).order_by(Level.order_index)
        ).all()
    )


def is_level_unlocked(db: Session, user: User, level: Level) -> bool:
    if _skips_sequential_lock(user):
        return True
    required = _required_levels(db)
    previous = [item for item in required if item.order_index < level.order_index]
    if not previous:
        return True
    last_prev = previous[-1]
    done = db.scalar(
        select(Progress).where(Progress.user_id == user.id, Progress.level_id == last_prev.id)
    )
    return done is not None


def completed_level_ids(db: Session, user: User) -> set[int]:
    rows = db.scalars(select(Progress.level_id).where(Progress.user_id == user.id)).all()
    return set(rows)


def hinted_level_ids(db: Session, user: User) -> set[int]:
    rows = db.scalars(select(HintUse.level_id).where(HintUse.user_id == user.id)).all()
    return set(rows)


def _honeypot_for(db: Session, submitted: str) -> Honeypot | None:
    digest = hash_flag(submitted)
    return db.scalar(select(Honeypot).where(Honeypot.flag_hash == digest))


def _clamp_score(user: User, delta: int) -> int:
    user.score = max(0, user.score + delta)
    return user.score


def _is_final_required(db: Session, level: Level) -> bool:
    required = _required_levels(db)
    return bool(required) and required[-1].id == level.id


def submit_flag(db: Session, user: User, level: Level, submitted: str, ip: str) -> dict:
    if not is_level_unlocked(db, user, level):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "LEVEL_LOCKED",
                "message": "Completa el nivel anterior primero.",
            },
        )

    honeypot = _honeypot_for(db, submitted)
    if honeypot is not None:
        delta = -abs(honeypot.penalty)
        _clamp_score(user, delta)
        db.add(
            Submission(
                user_id=user.id,
                level_id=level.id,
                result="honeypot",
                points_delta=delta,
                ip=ip,
            )
        )
        db.commit()
        db.refresh(user)
        return {
            "ok": False,
            "result": HONEYPOT_PUBLIC_RESULT,
            "points": user.score,
            "points_delta": delta,
            "unlocked_next": False,
            "message": "Envío inválido. Se aplicó una penalización.",
            "token": None,
        }

    existing = db.scalar(
        select(Progress).where(Progress.user_id == user.id, Progress.level_id == level.id)
    )
    if flags_match(submitted, level.flag_hash):
        if existing is not None:
            token_value = None
            if _is_final_required(db, level):
                token = issue_access_token(db, user)
                db.commit()
                token_value = token.token
            return {
                "ok": True,
                "result": "already_completed",
                "points": user.score,
                "points_delta": 0,
                "unlocked_next": False,
                "message": "Este nivel ya estaba completado.",
                "token": token_value,
            }

        user.score += level.points
        db.add(
            Progress(
                user_id=user.id,
                level_id=level.id,
                completed_at=datetime.now(timezone.utc),
                points_awarded=level.points,
            )
        )
        db.add(
            Submission(
                user_id=user.id,
                level_id=level.id,
                result="correct",
                points_delta=level.points,
                ip=ip,
            )
        )
        token_value = None
        unlocked_next = not _is_final_required(db, level)
        if _is_final_required(db, level):
            token = issue_access_token(db, user)
            token_value = token.token
            unlocked_next = False
        db.commit()
        db.refresh(user)
        return {
            "ok": True,
            "result": "correct",
            "points": user.score,
            "points_delta": level.points,
            "unlocked_next": unlocked_next,
            "message": "Nivel superado.",
            "token": token_value,
        }

    db.add(
        Submission(
            user_id=user.id,
            level_id=level.id,
            result="incorrect",
            points_delta=0,
            ip=ip,
        )
    )
    db.commit()
    return {
        "ok": False,
        "result": "incorrect",
        "points": user.score,
        "points_delta": 0,
        "unlocked_next": False,
        "message": "Flag incorrecta.",
        "token": None,
    }


def use_hint(db: Session, user: User, level: Level) -> dict:
    if not is_level_unlocked(db, user, level):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "LEVEL_LOCKED",
                "message": "Completa el nivel anterior primero.",
            },
        )

    existing = db.scalar(
        select(HintUse).where(HintUse.user_id == user.id, HintUse.level_id == level.id)
    )
    if existing is not None:
        return {
            "hint": level.hint_text,
            "already_used": True,
            "points_delta": 0,
            "score": user.score,
        }

    delta = -abs(level.hint_cost)
    _clamp_score(user, delta)
    db.add(HintUse(user_id=user.id, level_id=level.id))
    db.commit()
    db.refresh(user)
    return {
        "hint": level.hint_text,
        "already_used": False,
        "points_delta": delta,
        "score": user.score,
    }


def build_dashboard(db: Session, user: User) -> dict:
    levels = list(db.scalars(select(Level).order_by(Level.order_index)).all())
    done = completed_level_ids(db, user)
    hinted = hinted_level_ids(db, user)
    required = [level for level in levels if not level.is_bonus]
    cards = []
    for level in levels:
        if level.id in done:
            status = "completed"
        elif is_level_unlocked(db, user, level):
            status = "available"
        else:
            status = "locked"
        completed_at = None
        if status == "completed":
            row = db.scalar(
                select(Progress).where(Progress.user_id == user.id, Progress.level_id == level.id)
            )
            completed_at = row.completed_at if row else None
        cards.append(
            {
                "id": level.id,
                "order_index": level.order_index,
                "slug": level.slug,
                "title": level.title,
                "vector_name": level.vector_name,
                "lab_endpoint": level.lab_endpoint,
                "description": level.description,
                "points": level.points,
                "hint_cost": level.hint_cost,
                "is_bonus": level.is_bonus,
                "status": status,
                "hint_used": level.id in hinted,
                "completed_at": completed_at,
            }
        )

    token_row = db.scalar(select(AccessToken).where(AccessToken.user_id == user.id))
    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "student_code": user.student_code,
            "full_name": user.full_name,
            "score": user.score,
            "is_admin": user.is_admin,
            "created_at": user.created_at,
        },
        "completed": len([level for level in required if level.id in done]),
        "total": len(required),
        "levels": cards,
        "access_token": token_row.token if token_row else None,
        "token_expires_at": token_row.expires_at if token_row else None,
    }
