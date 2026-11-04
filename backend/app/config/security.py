"""Password hashing (Argon2id), access JWTs and opaque one-time/refresh tokens."""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.config.settings import settings

_hasher = PasswordHasher()  # argon2-cffi defaults to Argon2id
# Verified against when the email doesn't exist, so response timing doesn't reveal accounts.
_DUMMY_HASH = _hasher.hash("timing-equaliser-not-a-real-password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


# ── Access tokens (short-lived JWT, sent as Bearer) ──────────────────────────


def create_access_token(
    user_id: uuid.UUID, session_id: uuid.UUID, roles: list[str], permissions: list[str]
) -> tuple[str, int]:
    now = datetime.now(UTC)
    ttl = timedelta(minutes=settings.access_token_minutes)
    payload = {
        "sub": str(user_id),
        "sid": str(session_id),
        "type": "access",
        "roles": roles,
        "perms": permissions,
        "iat": now,
        "exp": now + ttl,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, int(ttl.total_seconds())


def decode_access_token(token: str) -> dict[str, Any]:
    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["exp", "sub", "sid", "type"]},
    )
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("wrong token type")
    return payload


# ── Opaque tokens (refresh tokens, email links). Only the hash is stored. ────


def new_opaque_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(48)
    return raw, hash_token(raw)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()
