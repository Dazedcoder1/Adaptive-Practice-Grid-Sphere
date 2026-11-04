"""Rate limiting and login monitoring."""

import logging
import time
import uuid

from sqlalchemy.orm import Session

from app.config.redis import get_redis
from app.modules.security.models import LoginEvent
from app.shared.exceptions import AppError

log = logging.getLogger(__name__)


class RateLimited(AppError):
    status_code = 429
    code = "rate_limited"


# When Redis is unreachable, stop trying for a while instead of making every sign-in
# wait for a connection timeout (on Windows a refused localhost connection takes seconds).
REDIS_RETRY_AFTER_SECONDS = 30.0
_redis_down_until = 0.0


def rate_limit(key: str, spec: str) -> None:
    """Fixed-window limiter. `spec` is "count/seconds", e.g. "10/60".

    Fails open if Redis is unavailable: authentication must keep working during a
    Redis outage; the failure is logged for monitoring.
    """
    global _redis_down_until
    if time.monotonic() < _redis_down_until:
        return
    limit, window = (int(x) for x in spec.split("/"))
    rkey = f"rl:{key}"
    try:
        r = get_redis()
        pipe = r.pipeline()
        pipe.incr(rkey)
        pipe.expire(rkey, window, nx=True)
        count, _ = pipe.execute()
    except Exception as e:  # noqa: BLE001
        _redis_down_until = time.monotonic() + REDIS_RETRY_AFTER_SECONDS
        log.warning(
            "Redis unavailable (%s); rate limiting paused for %ds — is Redis running?",
            e,
            REDIS_RETRY_AFTER_SECONDS,
        )
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
