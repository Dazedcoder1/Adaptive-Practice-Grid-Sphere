"""Test setup. Tests run against a THROWAWAY Postgres + Redis — never the real Neon DB.

TEST_DATABASE_URL  (default postgresql://postgres:postgres@localhost:5432/ap_test)
TEST_REDIS_URL     (default redis://localhost:6379/15)
"""

import os
import re
from urllib.parse import urlparse

_TEST_DB = os.getenv("TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ap_test")
_host = urlparse(_TEST_DB).hostname or ""
if _host not in {"localhost", "127.0.0.1", "postgres", "db"}:
    raise RuntimeError(
        f"Refusing to run tests against {_host!r}: tests TRUNCATE tables. "
        "Point TEST_DATABASE_URL at a local throwaway database."
    )

# Env vars override .env, so the real credentials there are never used by tests.
os.environ.update(
    DATABASE_URL=_TEST_DB,
    DATABASE_DIRECT_URL=_TEST_DB,
    REDIS_URL=os.getenv("TEST_REDIS_URL", "redis://localhost:6379/15"),
    JWT_SECRET="test-secret-test-secret-test-secret-123",
    ENVIRONMENT="test",
    EMAIL_BACKEND="console",
    FRONTEND_URL="http://localhost:3000",
    CORS_ORIGINS="http://localhost:3000",
    R2_ACCOUNT_ID="",
    R2_ACCESS_KEY_ID="",
    R2_SECRET_ACCESS_KEY="",
    R2_BUCKET_NAME="",
)

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.config.database import SessionLocal, engine, transaction  # noqa: E402
from app.config.redis import get_redis  # noqa: E402
from app.integrations import email  # noqa: E402

# Seeded by migrations — kept between tests.
_KEEP = {"alembic_version", "roles", "permissions", "role_permissions"}


@pytest.fixture(scope="session", autouse=True)
def _migrated_db():
    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def _clean_state(_migrated_db):
    with engine.begin() as conn:
        tables = conn.execute(
            text("select tablename from pg_tables where schemaname='public'")
        ).scalars()
        doomed = [t for t in tables if t not in _KEEP]
        if doomed:
            conn.execute(text(f"TRUNCATE {', '.join(doomed)} CASCADE"))
    get_redis().flushdb()
    email.outbox.clear()
    yield


@pytest.fixture
def client():
    with TestClient(app_instance(), base_url="http://localhost:8000") as c:
        yield c


def app_instance():
    from app.main import app

    return app


@pytest.fixture
def db():
    with SessionLocal() as s:
        yield s


# ── helpers ──────────────────────────────────────────────────────────────────

PASSWORD = "Str0ngPassw0rd"


def last_token(path: str) -> str:
    """Pull the token out of the most recent email whose link points at `path`."""
    for msg in reversed(email.outbox):
        m = re.search(rf"{re.escape(path)}\?token=([\w\-]+)", msg.body)
        if m:
            return m.group(1)
    raise AssertionError(f"no email with a {path} link; outbox={email.outbox}")


def register(client, email_addr="asha@example.com", **over):
    body = {
        "email": email_addr,
        "password": PASSWORD,
        "display_name": "Asha",
        "is_minor": False,
        "accept_terms": True,
        **over,
    }
    return client.post("/api/v1/auth/register", json=body)


def register_and_verify(client, email_addr="asha@example.com"):
    r = register(client, email_addr)
    assert r.status_code == 201, r.text
    r = client.post("/api/v1/auth/verify-email", json={"token": last_token("/verify-email")})
    assert r.status_code == 200, r.text


def login(client, email_addr="asha@example.com", password=PASSWORD, portal="student"):
    path = "/api/v1/auth/admin/login" if portal == "admin" else "/api/v1/auth/login"
    return client.post(path, json={"email": email_addr, "password": password})


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def student(client):
    register_and_verify(client)
    r = login(client)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture
def admin(db):
    from app.modules.identity.service import create_super_admin

    with transaction(db):
        create_super_admin(db, "admin@example.com", PASSWORD)
    return {"email": "admin@example.com", "password": PASSWORD}


@pytest.fixture
def admin_token(client, admin):
    # Separate client so the admin's refresh cookie doesn't clash with the student's.
    with TestClient(app_instance(), base_url="http://localhost:8000") as c:
        r = login(c, admin["email"], admin["password"], portal="admin")
        assert r.status_code == 200, r.text
        return r.json()["access_token"]
