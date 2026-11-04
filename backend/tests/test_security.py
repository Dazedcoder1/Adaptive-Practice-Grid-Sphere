import uuid

import jwt
import pytest

from app.config.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    hash_token,
    new_opaque_token,
    verify_password,
)
from app.config.settings import settings


def test_argon2id_roundtrip():
    h = hash_password("correct horse 1")
    assert h.startswith("$argon2id$")
    assert verify_password("correct horse 1", h)
    assert not verify_password("wrong", h)


def test_verify_against_missing_hash_is_false():
    assert verify_password("anything", None) is False


def test_access_token_roundtrip_and_tamper_detection():
    uid, sid = uuid.uuid4(), uuid.uuid4()
    token, ttl = create_access_token(uid, sid, ["student"], [])
    payload = decode_access_token(token)
    assert payload["sub"] == str(uid) and payload["sid"] == str(sid) and ttl == 900

    forged = jwt.encode({**payload, "roles": ["super_admin"]}, "wrong-secret", algorithm="HS256")
    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(forged)


def test_alg_none_rejected():
    uid, sid = uuid.uuid4(), uuid.uuid4()
    token = jwt.encode(
        {"sub": str(uid), "sid": str(sid), "type": "access", "exp": 9999999999},
        key=None,
        algorithm="none",
    )
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token)


def test_refresh_type_token_not_accepted_as_access():
    token = jwt.encode(
        {"sub": "x", "sid": "y", "type": "refresh", "exp": 9999999999},
        settings.jwt_secret,
        algorithm="HS256",
    )
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token)


def test_opaque_tokens_are_random_and_only_hash_is_kept():
    raw1, h1 = new_opaque_token()
    raw2, _ = new_opaque_token()
    assert raw1 != raw2 and len(raw1) >= 60
    assert hash_token(raw1) == h1 and raw1 not in h1


def test_spoofed_forwarded_for_is_ignored_and_junk_does_not_crash(client):
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "x@example.com",
            "password": "Str0ngPassw0rd",
            "display_name": "X",
            "is_minor": False,
            "accept_terms": True,
        },
        headers={"X-Forwarded-For": "not-an-ip, <script>"},
    )
    assert r.status_code == 201


def test_rate_limiter_does_not_stall_when_redis_is_down(monkeypatch):
    """Regression: with Redis stopped, every sign-in waited for a connection timeout."""
    from app.modules.security import service

    calls = []

    class Down:
        def pipeline(self):
            calls.append(1)
            raise ConnectionError("refused")

    monkeypatch.setattr(service, "get_redis", lambda: Down())
    monkeypatch.setattr(service, "_redis_down_until", 0.0)
    for _ in range(5):
        service.rate_limit("login:x", "10/60")  # fails open, never raises
    assert len(calls) == 1  # tried Redis once, then skipped it
