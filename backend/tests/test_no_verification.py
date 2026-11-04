"""REQUIRE_EMAIL_VERIFICATION=false (the current default): no verification step."""

import pytest
from sqlalchemy import select

from app.config.settings import settings
from app.integrations import email
from app.modules.identity.models import User, UserStatus
from tests.conftest import bearer, last_token, login, register


@pytest.fixture
def no_verification(monkeypatch):
    monkeypatch.setattr(settings, "require_email_verification", False)


def test_adult_can_sign_in_right_after_registering(client, no_verification):
    r = register(client)
    assert r.status_code == 201
    assert r.json()["status"] == "active"
    assert "sign in now" in r.json()["message"]
    assert email.outbox == []  # no verification email

    t = login(client)
    assert t.status_code == 200, t.text
    me = client.get("/api/v1/auth/me", headers=bearer(t.json()["access_token"]))
    assert me.json()["status"] == "active"


def test_minor_still_needs_guardian_consent(client, no_verification):
    r = register(client, "kid@example.com", is_minor=True, guardian_email="parent@example.com")
    assert r.json()["status"] == "pending_consent"
    assert email.outbox[-1].to == "parent@example.com"

    blocked = login(client, "kid@example.com")
    assert blocked.json()["error"]["code"] == "guardian_consent_pending"

    client.post("/api/v1/auth/guardian-consent", json={"token": last_token("/guardian-consent")})
    assert login(client, "kid@example.com").status_code == 200


def test_accounts_left_unverified_can_sign_in_once_turned_off(client, db, monkeypatch):
    register(client)  # created while verification was required
    assert login(client).json()["error"]["code"] == "email_not_verified"

    monkeypatch.setattr(settings, "require_email_verification", False)
    assert login(client).status_code == 200
    user = db.scalar(select(User).where(User.email == "asha@example.com"))
    assert user.status == UserStatus.ACTIVE
