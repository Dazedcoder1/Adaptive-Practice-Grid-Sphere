"""Auth lifecycle against a real Postgres: register → verify → login → refresh → logout."""

from sqlalchemy import select

from app.config.settings import settings
from app.integrations import email
from app.modules.identity.models import ConsentRecord, User, UserStatus
from app.modules.security.models import LoginEvent
from tests.conftest import PASSWORD, bearer, last_token, login, register, register_and_verify

COOKIE = settings.refresh_cookie_name


# ── Registration ─────────────────────────────────────────────────────────────


def test_register_creates_pending_student_with_consent_and_sends_email(client, db):
    r = register(client, "New@Example.com ")
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "pending_verification"

    user = db.scalar(select(User).where(User.email == "new@example.com"))
    assert user is not None and user.role_names == ["student"]
    assert user.password_hash.startswith("$argon2id$")
    kinds = {c.consent_type for c in db.scalars(select(ConsentRecord))}
    assert kinds == {"terms", "privacy"}
    assert email.outbox[-1].to == "new@example.com"


def test_register_rejects_duplicates_case_insensitively(client):
    assert register(client, "dup@example.com").status_code == 201
    r = register(client, "DUP@example.com")
    assert r.status_code == 409 and r.json()["error"]["code"] == "email_taken"


def test_register_validation(client):
    weak = register(client, password="short")
    assert weak.status_code == 422 and weak.json()["error"]["code"] == "validation_error"
    letters_only = register(client, password="onlyletterslong")
    assert letters_only.status_code == 422
    no_terms = register(client, accept_terms=False)
    assert no_terms.json()["error"]["code"] == "terms_required"
    minor_no_guardian = register(client, is_minor=True)
    assert minor_no_guardian.json()["error"]["code"] == "guardian_required"


# ── Verification & login gating ──────────────────────────────────────────────


def test_cannot_login_before_verification(client):
    register(client)
    r = login(client)
    assert r.status_code == 403 and r.json()["error"]["code"] == "email_not_verified"


def test_verification_token_is_single_use(client):
    register(client)
    token = last_token("/verify-email")
    assert client.post("/api/v1/auth/verify-email", json={"token": token}).status_code == 200
    again = client.post("/api/v1/auth/verify-email", json={"token": token})
    assert again.status_code == 400 and again.json()["error"]["code"] == "invalid_token"


def test_resend_verification_invalidates_old_link(client):
    register(client)
    old = last_token("/verify-email")
    client.post("/api/v1/auth/resend-verification", json={"email": "asha@example.com"})
    new = last_token("/verify-email")
    assert old != new
    assert client.post("/api/v1/auth/verify-email", json={"token": old}).status_code == 400
    assert client.post("/api/v1/auth/verify-email", json={"token": new}).status_code == 200


def test_minor_needs_guardian_consent(client, db):
    register(client, "kid@example.com", is_minor=True, guardian_email="parent@example.com")
    client.post("/api/v1/auth/verify-email", json={"token": last_token("/verify-email")})
    assert email.outbox[-1].to == "parent@example.com"

    blocked = login(client, "kid@example.com")
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "guardian_consent_pending"

    ok = client.post(
        "/api/v1/auth/guardian-consent", json={"token": last_token("/guardian-consent")}
    )
    assert ok.status_code == 200
    assert login(client, "kid@example.com").status_code == 200
    guardian = db.scalar(select(ConsentRecord).where(ConsentRecord.consent_type == "guardian"))
    assert guardian.granted_by == "guardian" and guardian.guardian_email == "parent@example.com"


def test_wrong_password_is_generic_and_logged(client, db):
    register_and_verify(client)
    bad = login(client, password="Wrong-passw0rd")
    unknown = login(client, "nobody@example.com")
    assert bad.status_code == unknown.status_code == 401
    assert bad.json() == unknown.json()  # doesn't reveal which emails exist
    events = db.scalars(select(LoginEvent).where(LoginEvent.success.is_(False))).all()
    assert {e.reason for e in events} == {"bad_credentials"}


def test_login_rate_limited(client):
    register_and_verify(client)
    codes = [login(client, password="Wrong-passw0rd").status_code for _ in range(11)]
    assert codes[:10] == [401] * 10 and codes[10] == 429


# ── Tokens, refresh rotation, logout ─────────────────────────────────────────


def test_login_returns_access_token_and_httponly_refresh_cookie(client):
    register_and_verify(client)
    r = login(client)
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["roles"] == ["student"] and body["user"]["display_name"] == "Asha"
    set_cookie = r.headers["set-cookie"]
    assert f"{COOKIE}=" in set_cookie and "HttpOnly" in set_cookie
    assert "Path=/api/v1/auth" in set_cookie and "SameSite=lax" in set_cookie

    me = client.get("/api/v1/auth/me", headers=bearer(body["access_token"]))
    assert me.status_code == 200 and me.json()["email"] == "asha@example.com"


def test_protected_routes_require_a_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers=bearer("garbage")).status_code == 401


def test_refresh_rotates_token(client, student):
    first = client.cookies.get(COOKIE)
    r = client.post("/api/v1/auth/refresh")
    assert r.status_code == 200
    second = client.cookies.get(COOKIE)
    assert second and second != first
    assert (
        client.get("/api/v1/auth/me", headers=bearer(r.json()["access_token"])).status_code == 200
    )


def test_refresh_token_reuse_revokes_whole_session(client, student):
    stolen = client.cookies.get(COOKIE)
    r = client.post("/api/v1/auth/refresh")  # legitimate rotation
    new_access = r.json()["access_token"]

    client.cookies.set(COOKIE, stolen, path="/api/v1/auth")  # attacker replays the old token
    replay = client.post("/api/v1/auth/refresh")
    assert replay.status_code == 401

    # Every token in that login family is now dead — including the legitimate one.
    assert client.get("/api/v1/auth/me", headers=bearer(new_access)).status_code == 401
    assert client.get("/api/v1/auth/me", headers=bearer(student["access_token"])).status_code == 401


def test_refresh_rejects_untrusted_origin(client, student):
    r = client.post("/api/v1/auth/refresh", headers={"Origin": "https://evil.example"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "bad_origin"


def test_logout_kills_refresh_and_access(client, student):
    access = student["access_token"]
    assert client.post("/api/v1/auth/logout").status_code == 200
    assert client.post("/api/v1/auth/refresh").status_code == 401
    assert client.get("/api/v1/auth/me", headers=bearer(access)).status_code == 401


def test_sessions_list_and_revoke_other_device(client, student):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app, base_url="http://localhost:8000") as phone:
        other = login(phone).json()["access_token"]

    sessions = client.get("/api/v1/auth/sessions", headers=bearer(student["access_token"])).json()
    assert len(sessions) == 2 and sum(s["current"] for s in sessions) == 1
    other_id = next(s["id"] for s in sessions if not s["current"])

    r = client.delete(f"/api/v1/auth/sessions/{other_id}", headers=bearer(student["access_token"]))
    assert r.status_code == 200
    assert client.get("/api/v1/auth/me", headers=bearer(other)).status_code == 401
    assert client.get("/api/v1/auth/me", headers=bearer(student["access_token"])).status_code == 200


def test_cannot_revoke_someone_elses_session(client, student):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app, base_url="http://localhost:8000") as c2:
        register_and_verify(c2, "ravi@example.com")
        ravi = login(c2, "ravi@example.com").json()["access_token"]
        ravi_session = c2.get("/api/v1/auth/sessions", headers=bearer(ravi)).json()[0]["id"]

    r = client.delete(
        f"/api/v1/auth/sessions/{ravi_session}", headers=bearer(student["access_token"])
    )
    assert r.status_code == 400
    assert client.get("/api/v1/auth/me", headers=bearer(ravi)).status_code == 200


# ── Passwords ────────────────────────────────────────────────────────────────


def test_password_reset_flow_revokes_all_sessions(client, student):
    r = client.post("/api/v1/auth/forgot-password", json={"email": "asha@example.com"})
    assert r.status_code == 202
    token = last_token("/reset-password")
    r = client.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": "N3wPassword!!"}
    )
    assert r.status_code == 200
    assert client.get("/api/v1/auth/me", headers=bearer(student["access_token"])).status_code == 401
    assert login(client).status_code == 401
    assert login(client, password="N3wPassword!!").status_code == 200


def test_forgot_password_does_not_reveal_accounts(client):
    a = client.post("/api/v1/auth/forgot-password", json={"email": "ghost@example.com"})
    assert a.status_code == 202 and email.outbox == []


def test_change_password_keeps_current_device_only(client, student):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app, base_url="http://localhost:8000") as phone:
        other = login(phone).json()["access_token"]

    wrong = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "nope", "new_password": "An0therPassword"},
        headers=bearer(student["access_token"]),
    )
    assert wrong.status_code == 400

    r = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "An0therPassword"},
        headers=bearer(student["access_token"]),
    )
    assert r.status_code == 200
    assert client.get("/api/v1/auth/me", headers=bearer(student["access_token"])).status_code == 200
    assert client.get("/api/v1/auth/me", headers=bearer(other)).status_code == 401


# ── Portals ──────────────────────────────────────────────────────────────────


def test_student_cannot_use_admin_login(client):
    register_and_verify(client)
    r = login(client, portal="admin")
    assert r.status_code == 403 and r.json()["error"]["code"] == "not_admin"


def test_admin_cannot_use_student_login(client, admin):
    r = login(client, admin["email"], admin["password"])
    assert r.status_code == 403 and r.json()["error"]["code"] == "use_admin_portal"


# ── Profile ──────────────────────────────────────────────────────────────────


def test_profile_read_update_and_deletion_request(client, student):
    h = bearer(student["access_token"])
    me = client.get("/api/v1/students/me", headers=h).json()
    assert me["display_name"] == "Asha" and me["timezone"] == "Asia/Kolkata"

    upd = client.patch(
        "/api/v1/students/me",
        json={"display_name": "Asha R", "timezone": "Asia/Dubai"},
        headers=h,
    )
    assert upd.status_code == 200 and upd.json()["display_name"] == "Asha R"
    bad_tz = client.patch("/api/v1/students/me", json={"timezone": "Mars/Base"}, headers=h)
    assert bad_tz.json()["error"]["code"] == "bad_timezone"

    req = client.post("/api/v1/students/me/deletion-request", headers=h)
    assert req.status_code == 200 and req.json()["deletion_requested_at"]
    cancel = client.delete("/api/v1/students/me/deletion-request", headers=h)
    assert cancel.json()["deletion_requested_at"] is None


def test_user_status_after_full_flow(db, student):
    user = db.scalar(select(User).where(User.email == "asha@example.com"))
    assert user.status == UserStatus.ACTIVE and user.last_login_at is not None


def test_sessions_and_admin_views_with_real_client_ips(admin):
    """Regression: INET values come back as ipaddress objects and must serialise."""
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app, base_url="http://localhost:8000", client=("203.0.113.7", 5000)) as c:
        register_and_verify(c)
        token = login(c).json()["access_token"]
        login(c, password="Wrong-passw0rd")
        sessions = c.get("/api/v1/auth/sessions", headers=bearer(token))
        assert sessions.status_code == 200, sessions.text
        assert sessions.json()[0]["ip_address"] == "203.0.113.7"

        admin_token = login(c, admin["email"], admin["password"], portal="admin").json()[
            "access_token"
        ]
        h = bearer(admin_token)
        uid = c.get("/api/v1/admin/users?q=asha", headers=h).json()["items"][0]["id"]
        for path in (f"/admin/users/{uid}", "/admin/login-events", "/admin/audit-logs"):
            r = c.get(f"/api/v1{path}", headers=h)
            assert r.status_code == 200, (path, r.text)
            assert "203.0.113.7" in r.text
