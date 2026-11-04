"""Super Admin APIs: RBAC, real statistics, suspension, audit trail."""

from tests.conftest import bearer, login, register, register_and_verify


def test_students_cannot_reach_admin_apis(client, student):
    h = bearer(student["access_token"])
    for path in ("/admin/stats", "/admin/users", "/admin/audit-logs", "/admin/login-events"):
        r = client.get(f"/api/v1{path}", headers=h)
        assert r.status_code == 403, path
        assert r.json()["error"]["code"] == "admin_only"


def test_admins_cannot_use_student_profile_apis(client, admin_token):
    r = client.get("/api/v1/students/me", headers=bearer(admin_token))
    assert r.status_code == 403 and r.json()["error"]["code"] == "student_only"


def test_stats_are_real_counts(client, admin_token):
    register_and_verify(client, "a@example.com")
    register(client, "b@example.com")  # unverified
    login(client, "a@example.com")
    login(client, "a@example.com", password="Wrong-passw0rd")

    s = client.get("/api/v1/admin/stats", headers=bearer(admin_token)).json()
    assert s["total_students"] == 2
    assert s["new_registrations_7d"] == 2
    assert s["pending_verification"] == 1
    assert s["active_students_7d"] == 1
    assert s["failed_logins_24h"] == 1
    assert s["failed_jobs"] == 0


def test_user_search_filter_and_paging(client, admin_token):
    for i in range(3):
        register_and_verify(client, f"student{i}@example.com")
    register(client, "pending@example.com")
    h = bearer(admin_token)

    page = client.get("/api/v1/admin/users?role=student&page_size=2", headers=h).json()
    assert page["total"] == 4 and len(page["items"]) == 2

    found = client.get("/api/v1/admin/users?q=student1", headers=h).json()
    assert [u["email"] for u in found["items"]] == ["student1@example.com"]

    pending = client.get("/api/v1/admin/users?status=pending_verification", headers=h).json()
    assert [u["email"] for u in pending["items"]] == ["pending@example.com"]


def test_suspend_takes_effect_immediately_and_is_audited(client, student, admin_token):
    h = bearer(admin_token)
    uid = student["user"]["id"]

    r = client.post(f"/api/v1/admin/users/{uid}/suspend", json={"reason": "spam"}, headers=h)
    assert r.status_code == 200 and r.json()["status"] == "suspended"
    assert r.json()["active_sessions"] == 0

    # Existing access token stops working at once; refresh and new logins are refused.
    assert client.get("/api/v1/auth/me", headers=bearer(student["access_token"])).status_code == 401
    assert client.post("/api/v1/auth/refresh").status_code == 401
    blocked = login(client)
    assert blocked.status_code == 403 and blocked.json()["error"]["code"] == "account_suspended"

    client.post(f"/api/v1/admin/users/{uid}/activate", json={}, headers=h)
    assert login(client).status_code == 200

    logs = client.get(f"/api/v1/admin/audit-logs?target_id={uid}", headers=h).json()["items"]
    actions = [entry["action"] for entry in logs]
    assert "user.suspended" in actions and "user.activated" in actions
    suspended = next(e for e in logs if e["action"] == "user.suspended")
    assert suspended["actor_email"] == "admin@example.com"
    assert suspended["details"] == {"reason": "spam"}


def test_admin_cannot_suspend_self(client, admin_token):
    me = client.get("/api/v1/auth/me", headers=bearer(admin_token)).json()
    r = client.post(f"/api/v1/admin/users/{me['id']}/suspend", json={}, headers=bearer(admin_token))
    assert r.status_code == 403 and r.json()["error"]["code"] == "self_action"


def test_user_detail_masks_guardian_email(client, admin_token):
    register(client, "kid@example.com", is_minor=True, guardian_email="parentname@example.com")
    h = bearer(admin_token)
    uid = client.get("/api/v1/admin/users?q=kid", headers=h).json()["items"][0]["id"]
    detail = client.get(f"/api/v1/admin/users/{uid}", headers=h).json()
    assert detail["guardian_email_masked"].startswith("pa") and "parentname" not in str(detail)


def test_login_events_filter(client, admin_token):
    register_and_verify(client)
    login(client, password="Wrong-passw0rd")
    r = client.get("/api/v1/admin/login-events?success=false", headers=bearer(admin_token)).json()
    assert r["total"] == 1 and r["items"][0]["reason"] == "bad_credentials"


def test_roles_listing(client, admin_token):
    roles = {
        r["name"]: r for r in client.get("/api/v1/admin/roles", headers=bearer(admin_token)).json()
    }
    assert roles["student"]["permissions"] == []
    assert "questions.approve" in roles["super_admin"]["permissions"]
