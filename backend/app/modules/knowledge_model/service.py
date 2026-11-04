"""Knowledge model: applies answer evidence to concept mastery (BKT) and answers queries.

The LLM never writes here — only graded attempts do, through `on_question_answered`.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.knowledge_model import bkt
from app.modules.knowledge_model.models import MasteryHistory, StudentMastery


def on_question_answered(db: Session, event_id: uuid.UUID, payload: dict) -> None:
    if payload.get("evaluation") == "ungraded":
        return  # subjective answers aren't evidence until reviewed
    student_id = uuid.UUID(payload["student_id"])
    attempt_id = uuid.UUID(payload["attempt_id"])
    now = datetime.fromisoformat(payload["answered_at"])
    for concept_id, weight in payload["concepts"]:
        row = db.scalar(
            select(StudentMastery)
            .where(StudentMastery.student_id == student_id, StudentMastery.concept_id == concept_id)
            .with_for_update()
        )
        if row is None:
            row = StudentMastery(
                student_id=student_id,
                concept_id=concept_id,
                p_known=bkt.PARAMS.p_init,
                attempts=0,
                correct=0,
                model_version=bkt.MODEL_VERSION,
            )
            db.add(row)
        before = row.p_known
        row.p_known = bkt.update(
            before,
            score=float(payload["score"]),
            question_type=payload["question_type"],
            hints_used=int(payload.get("hints_used", 0)),
            concept_weight=float(weight),
        )
        row.attempts += 1
        row.correct += 1 if payload["evaluation"] == "correct" else 0
        row.confidence = bkt.confidence(row.attempts)
        row.model_version = bkt.MODEL_VERSION
        row.last_practiced_at = now
        db.add(
            MasteryHistory(
                student_id=student_id,
                concept_id=concept_id,
                attempt_id=attempt_id,
                p_before=before,
                p_after=row.p_known,
                model_version=bkt.MODEL_VERSION,
                created_at=now,
            )
        )


def mastery_map(db: Session, student_id: uuid.UUID, concept_ids=None) -> dict[int, StudentMastery]:
    stmt = select(StudentMastery).where(StudentMastery.student_id == student_id)
    if concept_ids is not None:
        stmt = stmt.where(StudentMastery.concept_id.in_(list(concept_ids)))
    return {m.concept_id: m for m in db.scalars(stmt)}


def describe(m: StudentMastery | None) -> dict:
    if m is None:
        return {
            "p_known": None,
            "level": "not_started",
            "attempts": 0,
            "correct": 0,
            "confidence": 0.0,
            "last_practiced_at": None,
        }
    return {
        "p_known": round(m.p_known, 4),
        "level": bkt.level(m.p_known, m.attempts),
        "attempts": m.attempts,
        "correct": m.correct,
        "confidence": m.confidence,
        "last_practiced_at": m.last_practiced_at,
    }


def changes_for_attempt(db: Session, attempt_id: uuid.UUID) -> list[MasteryHistory]:
    return list(db.scalars(select(MasteryHistory).where(MasteryHistory.attempt_id == attempt_id)))


def now() -> datetime:
    return datetime.now(UTC)
