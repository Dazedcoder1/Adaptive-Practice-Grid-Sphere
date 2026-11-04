"""Helpers for learning-loop tests. Answer keys come from the DB — never from student APIs."""

import uuid

from app.config.database import SessionLocal, transaction
from app.modules.question_bank.models import QuestionVersion
from tests.conftest import bearer, login, register_and_verify


def seed():
    from scripts.seed_sample_content import seed as run

    with SessionLocal() as db, transaction(db):
        run(db)


def right_response(version_id) -> dict:
    with SessionLocal() as db:
        v = db.get(QuestionVersion, uuid.UUID(str(version_id)))
        t, a = v.type.value, v.answer
    if t in ("mcq_single", "diagram", "assertion_reason"):
        return {"selected": a["correct"]}
    if t == "mcq_multi":
        return {"selected": a["correct"]}
    if t in ("numerical", "integer"):
        return {"value": str(a["value"])}
    if t == "fill_blank":
        return {"values": [x[0] for x in a["accepted"]]}
    if t == "match":
        return {"pairs": a["pairs"]}
    return {"text": "An attempt at an explanation."}


def wrong_response(version_id) -> dict:
    with SessionLocal() as db:
        v = db.get(QuestionVersion, uuid.UUID(str(version_id)))
        t, a, c = v.type.value, v.answer, v.content
    if t in ("mcq_single", "diagram", "assertion_reason"):
        opts = [o["id"] for o in c.get("options", [{"id": x} for x in "abcd"])]
        return {"selected": next(o for o in opts if o != a["correct"])}
    if t == "mcq_multi":
        opts = [o["id"] for o in c["options"]]
        return {"selected": [o for o in opts if o not in a["correct"]][:1]}
    if t in ("numerical", "integer"):
        return {"value": str(a["value"] + 1000)}
    if t == "fill_blank":
        return {"values": ["zzz"] * len(a["accepted"])}
    if t == "match":
        keys = list(a["pairs"])
        vals = list(a["pairs"].values())
        return {"pairs": {k: vals[(i + 1) % len(vals)] for i, k in enumerate(keys)}}
    return {"text": "x"}


def onboarded_student(client, email="asha@example.com") -> dict:
    register_and_verify(client, email)
    token = login(client, email).json()["access_token"]
    h = bearer(token)
    opts = client.get("/api/v1/curriculum/options", headers=h).json()
    cbse = next(b for b in opts["boards"] if b["code"] == "CBSE")
    cur = cbse["curricula"][0]
    r = client.put(
        "/api/v1/students/me/onboarding",
        headers=h,
        json={
            "study_mode": "school",
            "curriculum_id": cur["id"],
            "subject_ids": [s["id"] for s in cur["subjects"]],
            "goals": ["strengthen_basics"],
            "weekly_days": 5,
            "minutes_per_day": 30,
        },
    )
    assert r.status_code == 200, r.text
    return {"h": h, "curriculum": cur}


def chapter_id(client, h, name="Laws of Motion") -> int:
    tree = client.get("/api/v1/curriculum/mine", headers=h).json()
    return next(ch["id"] for s in tree["subjects"] for ch in s["chapters"] if ch["name"] == name)


def answer(client, h, delivery, response, key=None):
    return client.post(
        "/api/v1/practice/attempts",
        headers={**h, "Idempotency-Key": key or uuid.uuid4().hex},
        json={"session_question_id": delivery["session_question_id"], "response": response},
    )
