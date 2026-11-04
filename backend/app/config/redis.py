from functools import lru_cache

import redis

from app.config.settings import settings


@lru_cache
def get_redis() -> redis.Redis:
    return redis.Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=1,
        socket_timeout=2,
    )
