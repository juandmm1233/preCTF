from collections import defaultdict
from time import time

from fastapi import HTTPException, status

WINDOW_SECONDS = 60
MAX_ATTEMPTS = 30

_attempts: dict[str, list[float]] = defaultdict(list)


def check_submit_rate(user_id: str) -> None:
    now = time()
    bucket = [stamp for stamp in _attempts[user_id] if now - stamp < WINDOW_SECONDS]
    if len(bucket) >= MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "RATE_LIMIT",
                "message": "Demasiados intentos. Espera un minuto.",
            },
        )
    bucket.append(now)
    _attempts[user_id] = bucket
