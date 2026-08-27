import hmac
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AccessToken, User

TOKEN_TTL_DAYS = 180


def _sign(payload: str) -> str:
    return hmac.new(
        settings.token_secret.encode("utf-8"),
        payload.encode("utf-8"),
        "sha256",
    ).hexdigest()[:16]


def issue_access_token(db: Session, user: User) -> AccessToken:
    existing = db.query(AccessToken).filter(AccessToken.user_id == user.id).one_or_none()
    if existing:
        return existing

    year = datetime.now(timezone.utc).year
    user8 = str(user.id).replace("-", "")[:8].upper()
    nonce = secrets.token_hex(4).upper()
    payload = f"PRECTF-UCC-{year}-{user8}-{nonce}"
    signature = _sign(payload)
    token = f"{payload}.{signature}"

    record = AccessToken(
        user_id=user.id,
        token=token,
        hmac_signature=signature,
        expires_at=datetime.now(timezone.utc) + timedelta(days=TOKEN_TTL_DAYS),
    )
    db.add(record)
    db.flush()
    return record


def parse_and_verify_signature(token: str) -> bool:
    if "." not in token:
        return False
    payload, signature = token.rsplit(".", 1)
    expected = _sign(payload)
    return hmac.compare_digest(signature, expected)
