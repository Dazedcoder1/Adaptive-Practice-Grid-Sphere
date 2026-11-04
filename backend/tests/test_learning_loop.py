"""End-to-end learning loop through the API (design §19.1 first milestone)."""

import json
import uuid

import pytest
from sqlalchemy import func, select

from app.modules.practice.models import QuestionAttempt
from app.seed.laws_of_motion import QUESTIONS
from app.shared.events import OutboxEvent
from tests.conftest import bearer, login, register_and_verify
from tests.learning_helpers import (
    answer,
    chapter_id,
    onboarded_student,
    right_response,
    seed,
    wrong_response,
)

FORBIDDEN_KEYS = {"answer", "solution", "correct", "accepted", "pairs", "model_answer", "value"}


@pytest.fixture(autouse=True)
def _content():
    seed()


def _start(client, h, mode="adaptive", **scope):
    r = client.post("/api/v1/practice/sessions", headers=h, json={"mode": mode, **scope})
    assert r.status_code == 201, r.text
    return r.json()


def _next(client, h, sid):
    r = client.post(f"/api/v1/practice/sessions/{sid}/next", headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def _walk_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _walk_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_keys(v)


def test_seeded_answer_keys_are_self_consistent():
    from app.modules.question_bank.evaluation import evaluate
    from app.modules.question_bank.models import QuestionType

    for q in QUESTIONS:
        if q["type"] == "subjective":
            continue
        a, t = q["answer"], QuestionType(q["type"])
        resp = (
            {"selected": a["correct"]}
            if "correct" in a
            else {"value": str(a["value"])}
            if "value" in a
            else {"values": [x[0] for x in a["accepted"]]}
            if "accepted" in a
            else {"pairs": a["pairs"]}
        )
        assert evaluate(t, q["content"], a, resp).is_correct, q["stem"]


def test_onboarding_and_curriculum_view(client):
    s = onboarded_student(client)
    me = client.get("/api/v1/auth/me", headers=s["h"]).json()
    assert me["onboarding_completed"] is True
    tree = client.get("/api/v1/curriculum/mine", headers=s["h"]).json()
    chapters = [ch["name"] for sub in tree["subjects"] for ch in sub["chapters"]]
    assert chapters == ["Motion in a Straight Line", "Laws of Motion"]
    concept = tree["subjects"][0]["chapters"][1]["topics"][0]["concepts"][2]
    assert concept["code"] == "N2" and concept["level"] == "not_started"
    assert concept["question_count"] >= 5 and len(concept["prerequisite_ids"]) == 3

    detail = client.get(f"/api/v1/curriculum/concepts/{concept['id']}", headers=s["h"]).json()
    assert {p["code"] for p in detail["prerequisites"]} == {"N1", "MOM", "KIN"}
    assert "F_{net}" in detail["description"]
    hits = client.get("/api/v1/curriculum/search?q=friction", headers=s["h"]).json()
    assert any(h["code"] == "FRIC" for h in hits)


def test_onboarding_rejects_mismatched_mode(client):
    register_and_verify(client)
    h = bearer(login(client).json()["access_token"])
    cur = client.get("/api/v1/curriculum/options", headers=h).json()["boards"]
    cbse = next(b for b in cur if b["code"] == "CBSE")["curricula"][0]
    r = client.put(
        "/api/v1/students/me/onboarding",
        headers=h,
        json={"study_mode": "jee", "curriculum_id": cbse["id"], "subject_ids": [1]},
    )
    assert r.json()["error"]["code"] == "mode_mismatch"


def test_adaptive_session_full_loop(client, db):
    s = onboarded_student(client)
    h = s["h"]
    sess = _start(client, h, chapter_id=chapter_id(client, h), count=6)
    assert sess["target_count"] == 6 and sess["status"] == "active"

    d1 = _next(client, h, sess["id"])
    # The delivered question never carries answer data.
    assert FORBIDDEN_KEYS.isdisjoint(set(_walk_keys(d1["question"]["content"])))
    assert "solution" not in d1["question"] and "answer" not in d1["question"]
    assert d1["why"]
    # Asking again returns the same pending question (session recovery).
    assert _next(client, h, sess["id"])["session_question_id"] == d1["session_question_id"]

    key = uuid.uuid4().hex
    fb = answer(client, h, d1, right_response(d1["question"]["version_id"]), key)
    assert fb.status_code == 200, fb.text
    fb = fb.json()
    assert fb["evaluation"] == "correct" and fb["correct_answer"]
    assert fb["mastery_changes"] and all(c["after"] > c["before"] for c in fb["mastery_changes"])

    # Retrying with the same key returns the same result and never double-counts.
    replay = answer(client, h, d1, right_response(d1["question"]["version_id"]), key).json()
    assert replay["attempt_id"] == fb["attempt_id"] and replay["session"]["answered_count"] == 1
    again = answer(client, h, d1, right_response(d1["question"]["version_id"]))
    assert again.status_code == 409 and again.json()["error"]["code"] == "already_answered"
    assert db.scalar(select(func.count()).select_from(QuestionAttempt)) == 1
    # The outbox event was written and (inline) processed.
    ev = db.scalar(select(OutboxEvent).where(OutboxEvent.event_type == "QuestionAnswered"))
    assert ev.published_at is not None

    seen = {d1["question"]["question_id"]}
    for _ in range(5):
        d = _next(client, h, sess["id"])
        if d["finished"]:
            break
        assert d["question"]["question_id"] not in seen  # never repeats within a session
        seen.add(d["question"]["question_id"])
        answer(client, h, d, wrong_response(d["question"]["version_id"]))
    done = _next(client, h, sess["id"])
    assert done["finished"] and done["session"]["status"] == "completed"

    rep = client.get(f"/api/v1/practice/sessions/{sess['id']}/report", headers=h).json()
    assert len(rep["questions"]) == 6 and rep["concepts"]
    assert 0 < rep["accuracy"] < 1 and rep["weak_concepts"]

    weak = client.get("/api/v1/adaptive/weak-concepts", headers=h).json()
    assert weak and all(w["level"] in ("weak", "developing") for w in weak)
    queue = client.get("/api/v1/revision/queue", headers=h).json()
    assert queue["upcoming"] and queue["upcoming"][0]["concept"]["name"]
    notebook = client.get("/api/v1/error-notebook", headers=h).json()
    assert len(notebook) >= 1 and notebook[0]["your_answer"] and notebook[0]["correct_answer"]

    dash = client.get("/api/v1/analytics/dashboard", headers=h).json()
    assert dash["questions_attempted"] == 6 and dash["streak_days"] == 1
    assert dash["concepts_practised"] >= 1 and dash["weak_concepts"]
    assert dash["recommendations"]


def test_hints_pause_resume_and_complete(client):
    s = onboarded_student(client)
    h = s["h"]
    sess = _start(client, h, chapter_id=chapter_id(client, h, "Motion in a Straight Line"))
    d = _next(client, h, sess["id"])
    while d["question"]["hints_available"] == 0:  # find a question with a hint
        answer(client, h, d, right_response(d["question"]["version_id"]))
        d = _next(client, h, sess["id"])
    url = f"/api/v1/practice/sessions/{sess['id']}/questions/{d['session_question_id']}/hint"
    hint = client.post(url, headers=h).json()
    assert len(hint["hints"]) == 1
    assert _next(client, h, sess["id"])["question"]["hints"] == hint["hints"]

    client.post(f"/api/v1/practice/sessions/{sess['id']}/pause", headers=h)
    blocked = client.post(f"/api/v1/practice/sessions/{sess['id']}/next", headers=h)
    assert blocked.json()["error"]["code"] == "paused"
    assert answer(client, h, d, right_response(d["question"]["version_id"])).status_code == 409
    client.post(f"/api/v1/practice/sessions/{sess['id']}/resume", headers=h)
    fb = answer(client, h, d, right_response(d["question"]["version_id"])).json()
    assert fb["evaluation"] == "correct"
    r = client.post(f"/api/v1/practice/sessions/{sess['id']}/complete", headers=h).json()
    assert r["status"] == "completed"


def test_diagnostic_covers_each_concept_once(client):
    s = onboarded_student(client)
    h = s["h"]
    sess = _start(client, h, "diagnostic", chapter_id=chapter_id(client, h))
    assert sess["target_count"] == 10  # ten concepts in Laws of Motion
    concepts = []
    while not (d := _next(client, h, sess["id"]))["finished"]:
        concepts.append(tuple(c["id"] for c in d["question"]["concepts"]))
        answer(client, h, d, right_response(d["question"]["version_id"]))
    assert len(concepts) == 10


def test_invalid_responses_and_missing_idempotency_key(client):
    s = onboarded_student(client)
    h = s["h"]
    sess = _start(client, h, concept_ids=[_concept(client, h, "KIN")])
    d = _next(client, h, sess["id"])
    no_key = client.post(
        "/api/v1/practice/attempts",
        headers=h,
        json={"session_question_id": d["session_question_id"], "response": {}},
    )
    assert no_key.json()["error"]["code"] == "idempotency_key_required"
    bad = answer(client, h, d, {"nonsense": True})
    assert bad.status_code == 400 and bad.json()["error"]["code"] == "invalid_response"


def _concept(client, h, code):
    tree = client.get("/api/v1/curriculum/mine", headers=h).json()
    return next(
        c["id"]
        for s in tree["subjects"]
        for ch in s["chapters"]
        for t in ch["topics"]
        for c in t["concepts"]
        if c["code"] == code
    )


def test_other_students_cannot_touch_my_session(client):
    from fastapi.testclient import TestClient

    from app.main import app

    s = onboarded_student(client)
    sess = _start(client, s["h"], concept_ids=[_concept(client, s["h"], "N2")])
    d = _next(client, s["h"], sess["id"])
    with TestClient(app, base_url="http://localhost:8000") as c2:
        other = onboarded_student(c2, "ravi@example.com")["h"]
        assert (
            c2.post(f"/api/v1/practice/sessions/{sess['id']}/next", headers=other).status_code
            == 404
        )
        assert (
            c2.get(f"/api/v1/practice/sessions/{sess['id']}/report", headers=other).status_code
            == 404
        )
        steal = answer(c2, other, d, right_response(d["question"]["version_id"]))
        assert steal.status_code == 404


def test_error_notebook_review_cycle(client):
    s = onboarded_student(client)
    h = s["h"]
    sess = _start(client, h, concept_ids=[_concept(client, h, "N3")], count=1)
    d = _next(client, h, sess["id"])
    answer(client, h, d, wrong_response(d["question"]["version_id"]))
    entry = client.get("/api/v1/error-notebook", headers=h).json()[0]
    assert entry["times_wrong"] == 1 and entry["status"] == "open"

    upd = client.patch(
        f"/api/v1/error-notebook/{entry['id']}",
        headers=h,
        json={"category": "concept", "note": "Mixed up which body"},
    ).json()
    assert upd["category"] == "concept" and upd["note"] == "Mixed up which body"

    review = _start(client, h, "review", question_ids=[entry["question_id"]])
    d2 = _next(client, h, review["id"])
    assert d2["question"]["question_id"] == entry["question_id"]
    answer(client, h, d2, right_response(d2["question"]["version_id"]))
    after = client.get("/api/v1/error-notebook", headers=h).json()[0]
    assert after["times_right_since"] == 1

    resolved = client.patch(
        f"/api/v1/error-notebook/{entry['id']}", headers=h, json={"status": "resolved"}
    ).json()
    assert resolved["status"] == "resolved" and resolved["resolved_at"]
    assert client.delete(f"/api/v1/error-notebook/{entry['id']}", headers=h).status_code == 204


def test_revision_session_only_when_due(client):
    s = onboarded_student(client)
    r = client.post("/api/v1/practice/sessions", headers=s["h"], json={"mode": "revision"})
    assert r.json()["error"]["code"] == "nothing_due"


def test_events_survive_when_inline_processing_fails(client, db, monkeypatch):
    """An acknowledged answer is durable even if consumers crash: the event stays
    unpublished for the worker to retry."""
    from app.modules.knowledge_model import service as knowledge

    def boom(*a, **k):
        raise RuntimeError("consumer down")

    monkeypatch.setattr(knowledge, "on_question_answered", boom)
    s = onboarded_student(client)
    sess = _start(client, s["h"], concept_ids=[_concept(client, s["h"], "KIN")])
    d = _next(client, s["h"], sess["id"])
    fb = answer(client, s["h"], d, right_response(d["question"]["version_id"]))
    assert fb.status_code == 200 and fb.json()["mastery_pending"] is True
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(QuestionAttempt)) == 1
    ev = db.scalar(select(OutboxEvent).where(OutboxEvent.event_type == "QuestionAnswered"))
    assert ev.published_at is None  # left for the relay


def test_payload_never_leaks_answer_for_any_seeded_type(client):
    s = onboarded_student(client)
    h = s["h"]
    types = set()
    for code in ("N1", "N2", "FBD", "CIRC", "FRIC"):
        sess = _start(client, h, concept_ids=[_concept(client, h, code)], count=30)
        while not (d := _next(client, h, sess["id"]))["finished"]:
            types.add(d["question"]["type"])
            raw = json.dumps(d["question"])
            assert '"correct"' not in raw and '"accepted"' not in raw and '"pairs"' not in raw
            answer(client, h, d, right_response(d["question"]["version_id"]))
    assert {
        "mcq_single",
        "mcq_multi",
        "numerical",
        "fill_blank",
        "match",
        "assertion_reason",
        "subjective",
    } <= types


def test_dashboard_revision_items_carry_concept_names(client):
    from tests.learning_helpers import answer, chapter_id, onboarded_student, wrong_response

    h = onboarded_student(client)["h"]
    s = client.post(
        "/api/v1/practice/sessions",
        headers=h,
        json={"mode": "adaptive", "chapter_id": chapter_id(client, h), "count": 3},
    ).json()
    for _ in range(3):
        d = client.post(f"/api/v1/practice/sessions/{s['id']}/next", headers=h).json()
        assert answer(client, h, d, wrong_response(d["question"]["version_id"])).status_code == 200
    d = client.get("/api/v1/analytics/dashboard", headers=h).json()
    items = d["revision_upcoming"]
    assert items, d
    assert all(i["concept"] and i["concept"]["name"] for i in items)
    assert all("level" in i["mastery"] for i in items)


def test_new_student_starts_with_foundations_not_advanced_concepts(client):
    """Regression: exploration once served 'Connected bodies' (difficulty 4) as a first question."""
    from tests.learning_helpers import answer, onboarded_student, right_response

    h = onboarded_student(client)["h"]
    tree = client.get("/api/v1/curriculum/mine", headers=h).json()
    chapter = next(
        ch for sub in tree["subjects"] for ch in sub["chapters"] if ch["name"] == "Laws of Motion"
    )
    # A chapter session only weighs prerequisites inside that chapter.
    prereqs = {c["id"]: c["prerequisite_ids"] for t in chapter["topics"] for c in t["concepts"]}
    s = client.post(
        "/api/v1/practice/sessions",
        headers=h,
        json={"mode": "adaptive", "chapter_id": chapter["id"], "count": 5},
    ).json()
    practised: set[int] = set()
    for _ in range(5):
        d = client.post(f"/api/v1/practice/sessions/{s['id']}/next", headers=h).json()
        cid = d["question"]["concepts"][0]["id"]
        unmet = [p for p in prereqs.get(cid, []) if p in prereqs and p not in practised]
        assert not unmet, (d["why"], cid, unmet)
        practised.add(cid)
        answer(client, h, d, right_response(d["question"]["version_id"]))
