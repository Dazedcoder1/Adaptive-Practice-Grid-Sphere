"""Rate limiting and login monitoring."""

import logging
import uuid

from sqlalchemy.orm import Session

from app.config.redis import get_redis
from app.modules.security.models import LoginEvent
from app.shared.exceptions import AppError

log = logging.getLogger(__name__)


class RateLimited(AppError):
    status_code = 429
    code = "rate_limited"


def rate_limit(key: str, spec: str) -> None:
    """Fixed-window limiter. `spec` is "count/seconds", e.g. "10/60".

    Fails open if Redis is unavailable: authentication must keep working during a
    Redis outage; the failure is logged for monitoring.
    """
    limit, window = (int(x) for x in spec.split("/"))
    rkey = f"rl:{key}"
    try:
        r = get_redis()
        pipe = r.pipeline()
        pipe.incr(rkey)
        pipe.expire(rkey, window, nx=True)
        count, _ = pipe.execute()
    except Exception:  # noqa: BLE001
        log.warning("rate limiter unavailable; allowing request", exc_info=True)
        return
    if int(count) > limit:
        raise RateLimited("Too many attempts. Please wait a moment and try again.")


def record_login(
    db: Session,
    *,
    email: str,
    portal: str,
    success: bool,
    user_id: uuid.UUID | None = None,
    reason: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    db.add(
        LoginEvent(
            user_id=user_id,
            email=email,
            portal=portal,
            success=success,
            reason=reason,
            ip_address=ip,
            user_agent=user_agent,
        )
    )
