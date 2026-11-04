"""Super Admin content management: curriculum graph and question lifecycle."""

import pytest
from sqlalchemy import select

from app.modules.practice.models import QuestionAttempt
from tests.conftest import bearer
from tests.learning_helpers import answer, onboarded_student, right_response, seed

Q = {
    "type": "numerical",
    "difficulty": 2,
    "stem": "What is 2 + 2?",
    "content": {"unit": ""},
    "answer": {"value": 4},
    "solution": "Four.",
    "hints": ["Count."],
    "concepts": [],
}


@pytest.fixture(autouse=True)
def _content():
    seed()


@pytest.fixture
def h(admin_token):
    return bearer(admin_token)


def _concepts(client, h):
    cur = client.get("/api/v1/admin/curriculum/curricula", headers=h).json()[0]
    tree = client.get(f"/api/v1/admin/curriculum/curricula/{cur['id']}/tree", headers=h).json()
    return cur, {
        c["code"]: c
        for s in tree["subjects"]
        for ch in s["chapters"]
        for t in ch["topics"]
        for c in t["concepts"]
    }


def test_students_cannot_manage_content(client):
    s = onboarded_student(client)
    for path in ("/admin/curriculum/curricula", "/admin/questions"):
        assert client.get(f"/api/v1{path}", headers=s["h"]).status_code == 403


def test_build_curriculum_and_prerequisites(client, h):
    boards = client.get("/api/v1/admin/curriculum/boards", headers=h).json()
    grades = client.get("/api/v1/admin/curriculum/grades", headers=h).json()
    cbse = next(b for b in boards if b["code"] == "CBSE")
    g12 = next(g for g in grades if g["name"] == "Class 12")
    cid = client.post(
        "/api/v1/admin/curriculum/curricula",
        headers=h,
        json={
            "board_id": cbse["id"],
            "grade_id": g12["id"],
            "name": "CBSE Class 12",
            "version": "2026-27",
        },
    ).json()["id"]
    sid = client.post(
        "/api/v1/admin/curriculum/subjects", headers=h, json={"parent_id": cid, "name": "Chemistry"}
    ).json()["id"]
    chid = client.post(
        "/api/v1/admin/curriculum/chapters", headers=h, json={"parent_id": sid, "name": "Solutions"}
    ).json()["id"]
    tid = client.post(
        "/api/v1/admin/curriculum/topics",
        headers=h,
        json={"parent_id": chid, "name": "Concentration"},
    ).json()["id"]
    a = client.post(
        "/api/v1/admin/curriculum/concepts",
        headers=h,
        json={"parent_id": tid, "name": "Molarity", "code": "MOLARITY"},
    ).json()["id"]
    b = client.post(
        "/api/v1/admin/curriculum/concepts",
        headers=h,
        json={"parent_id": tid, "name": "Dilution", "code": "DILUTION"},
    ).json()["id"]

    ok = client.put(
        f"/api/v1/admin/curriculum/concepts/{b}/prerequisites",
        headers=h,
        json={"prerequisite_ids": [a]},
    )
    assert ok.json()["prerequisite_ids"] == [a]
    loop = client.put(
        f"/api/v1/admin/curriculum/concepts/{a}/prerequisites",
        headers=h,
        json={"prerequisite_ids": [b]},
    )
    assert loop.status_code == 400 and loop.json()["error"]["code"] == "prerequisite_cycle"

    # Draft curricula aren't offered to students until published.
    s = onboarded_student(client)
    names = [
        c["name"]
        for bd in client.get("/api/v1/curriculum/options", headers=s["h"]).json()["boards"]
        for c in bd["curricula"]
    ]
    assert "CBSE Class 12" not in names
    client.patch(
        f"/api/v1/admin/curriculum/curricula/{cid}", headers=h, json={"status": "published"}
    )
    names = [
        c["name"]
        for bd in client.get("/api/v1/curriculum/options", headers=s["h"]).json()["boards"]
        for c in bd["curricula"]
    ]
    assert "CBSE Class 12" in names

    # Empty concept can be deleted; export → import round-trips under a new version.
    exported = client.get(f"/api/v1/admin/curriculum/curricula/{cid}/export", headers=h).json()
    assert exported["subjects"][0]["chapters"][0]["topics"][0]["concepts"][1]["prerequisites"] == [
        "MOLARITY"
    ]
    exported["version"] = "2027-28"
    assert (
        client.post(
            "/api/v1/admin/curriculum/curricula/import", headers=h, json=exported
        ).status_code
        == 201
    )
    assert client.delete(f"/api/v1/admin/curriculum/concepts/{b}", headers=h).status_code == 204


def test_cannot_delete_concepts_with_questions_or_progress(client, h):
    _, concepts = _concepts(client, h)
    r = client.delete(f"/api/v1/admin/curriculum/concepts/{concepts['N2']['id']}", headers=h)
    assert r.status_code == 409 and r.json()["error"]["code"] == "has_activity"


def test_question_validation(client, h):
    _, concepts = _concepts(client, h)
    bad = {
        **Q,
        "type": "mcq_single",
        "content": {"options": [{"id": "a", "text": "x"}, {"id": "b", "text": "y"}]},
        "answer": {"correct": "z"},
        "concepts": [{"concept_id": concepts["N1"]["id"]}],
    }
    r = client.post("/api/v1/admin/questions", headers=h, json=bad)
    assert r.status_code == 400 and "correct option" in r.json()["error"]["message"]
    no_concept = client.post("/api/v1/admin/questions", headers=h, json=Q)
    assert no_concept.status_code == 422


def test_lifecycle_and_versioning_preserve_history(client, h, db):
    _, concepts = _concepts(client, h)
    cid = concepts["KIN"]["id"]
    q = client.post(
        "/api/v1/admin/questions", headers=h, json={**Q, "concepts": [{"concept_id": cid}]}
    ).json()
    assert q["status"] == "draft"
    qid = q["id"]
    assert (
        client.post(f"/api/v1/admin/questions/{qid}/submit", headers=h).json()["status"]
        == "in_review"
    )
    rej = client.post(
        f"/api/v1/admin/questions/{qid}/reject", headers=h, json={"note": "Needs units"}
    ).json()
    assert rej["status"] == "rejected" and rej["latest"]["review_note"] == "Needs units"
    client.put(
        f"/api/v1/admin/questions/{qid}", headers=h, json={**Q, "concepts": [{"concept_id": cid}]}
    )
    client.post(f"/api/v1/admin/questions/{qid}/submit", headers=h)
    pub = client.post(f"/api/v1/admin/questions/{qid}/publish", headers=h, json={}).json()
    assert pub["status"] == "published" and pub["latest"]["version"] == 1
    v1 = pub["published_version_id"]

    # A student answers version 1.
    s = onboarded_student(client)
    sess = client.post(
        "/api/v1/practice/sessions", headers=s["h"], json={"concept_ids": [cid], "count": 30}
    ).json()
    while not (
        d := client.post(f"/api/v1/practice/sessions/{sess['id']}/next", headers=s["h"]).json()
    )["finished"]:
        answer(client, s["h"], d, right_response(d["question"]["version_id"]))
        if d["question"]["question_id"] == qid:
            break
    assert d["question"]["version_id"] == v1

    # Editing a published question creates v2 as a draft; students keep getting v1.
    edited = client.put(
        f"/api/v1/admin/questions/{qid}",
        headers=h,
        json={**Q, "stem": "What is 3 + 1?", "concepts": [{"concept_id": cid}]},
    ).json()
    assert edited["latest"]["version"] == 2 and edited["published_version_id"] == v1
    assert edited["status"] == "published_with_draft"
    client.post(f"/api/v1/admin/questions/{qid}/publish", headers=h, json={})
    detail = client.get(f"/api/v1/admin/questions/{qid}", headers=h).json()
    assert [v["status"] for v in detail["versions"]] == ["published", "superseded"]

    # The student's attempt still points at the version they actually saw.
    a = db.scalar(select(QuestionAttempt).where(QuestionAttempt.question_id == qid))
    assert str(a.question_version_id) == v1
    rep = client.get(f"/api/v1/practice/sessions/{sess['id']}/report", headers=s["h"]).json()
    assert "What is 2 + 2?" in [x["stem"] for x in rep["questions"]]


def test_archived_questions_are_not_served(client, h):
    _, concepts = _concepts(client, h)
    listed = client.get(
        f"/api/v1/admin/questions?concept_id={concepts['EQ']['id']}", headers=h
    ).json()
    for item in listed["items"]:
        client.post(f"/api/v1/admin/questions/{item['id']}/archive", headers=h)
    s = onboarded_student(client)
    r = client.post(
        "/api/v1/practice/sessions", headers=s["h"], json={"concept_ids": [concepts["EQ"]["id"]]}
    )
    assert r.json()["error"]["code"] == "no_questions"


def test_bulk_import_is_all_or_nothing(client, h):
    _, concepts = _concepts(client, h)
    good = {**Q, "concepts": [{"concept_id": concepts["KIN"]["id"]}]}
    bad = {**good, "type": "integer", "answer": {"value": 2.5}}
    before = client.get("/api/v1/admin/questions/stats", headers=h).json()["questions_total"]
    r = client.post("/api/v1/admin/questions/import", headers=h, json={"questions": [good, bad]})
    assert r.status_code == 400 and r.json()["error"]["message"].startswith("Question 2:")
    assert (
        client.get("/api/v1/admin/questions/stats", headers=h).json()["questions_total"] == before
    )
    ok = client.post(
        "/api/v1/admin/questions/import",
        headers=h,
        json={"questions": [good, good], "publish": True},
    )
    assert ok.status_code == 201 and len(ok.json()["created"]) == 2


def test_admin_stats_include_learning_metrics(client, h):
    stats = client.get("/api/v1/admin/stats", headers=h).json()
    assert stats["questions_published"] == 38 and stats["concepts_total"] == 11
    assert stats["concepts_with_questions"] == 11 and stats["approval_backlog"] == 0
