import logging
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, Response
from sqlalchemy import text

from app.config.database import engine
from app.config.redis import get_redis
from app.config.settings import settings
from app.integrations import storage
from app.modules import api_router
from app.shared.exceptions import register_exception_handlers
from app.shared.middleware import register_middleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    docs_url=f"{settings.api_v1_prefix}/docs",
)
register_middleware(app)
register_exception_handlers(app)
app.include_router(api_router, prefix=settings.api_v1_prefix)

if settings.environment == "test":  # E2E helpers; never mounted in development or production
    from app.shared.testing import router as testing_router

    app.include_router(testing_router, prefix=settings.api_v1_prefix)


def _check_db() -> str:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return "ok"


def _check_redis() -> str:
    get_redis().ping()
    return "ok"


def _check_r2() -> str:
    if not settings.r2_configured:
        return "not configured"
    storage.check()
    return "ok"


@app.get(f"{settings.api_v1_prefix}/health", tags=["system"])
def health(response: Response) -> dict[str, str]:
    """Liveness + dependency check: database, redis, R2."""
    checks = {"database": _check_db, "redis": _check_redis, "r2": _check_r2}
    result: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {name: pool.submit(fn) for name, fn in checks.items()}
        for name, fut in futures.items():
            try:
                result[name] = fut.result(timeout=10)
            except Exception as e:  # noqa: BLE001 — report any dependency failure
                result[name] = f"error: {type(e).__name__}: {e}"[:300]
    if any(v.startswith("error") for v in result.values()):
        response.status_code = 503
    return result
