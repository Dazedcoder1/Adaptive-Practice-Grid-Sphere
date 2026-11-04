"""Revision queue: each practised concept gets a spaced-repetition schedule driven by the
student's answers. Practising a concept (in any mode) reschedules it."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.revision.models import RevisionItem
from app.modules.revision.scheduler import Schedule, next_schedule, retention_estimate

PRIMARY_WEIGHT = 0.5  # only concepts a question substantially tests are scheduled


def on_question_answered(db: Session, event_id: uuid.UUID, payload: dict) -> None:
    if payload.get("evaluation") == "ungraded":
        return
    student_id = uuid.UUID(payload["student_id"])
    now = datetime.fromisoformat(payload["answered_at"])
    correct = payload["evaluation"] == "correct"
    for concept_id, weight in payload["concepts"]:
        if weight < PRIMARY_WEIGHT:
            continue
        item = db.scalar(
            select(RevisionItem)
            .where(RevisionItem.student_id == student_id, RevisionItem.concept_id == concept_id)
            .with_for_update()
        )
        prev = None
        if item:
            # Several questions on one concept in a sitting count as one review.
            if (
                correct
                and item.last_reviewed_at
                and now - item.last_reviewed_at < timedelta(hours=6)
                and item.repetitions > 0
            ):
                continue
            prev = Schedule(
                item.interval_days,
                item.ease,
                item.repetitions,
                item.lapses,
                item.due_at,
                item.reason,
            )
        s = next_schedule(prev, correct=correct, now=now)
        if item is None:
            item = RevisionItem(student_id=student_id, concept_id=concept_id)
            db.add(item)
        item.interval_days, item.ease = s.interval_days, s.ease
        item.repetitions, item.lapses = s.repetitions, s.lapses
        item.due_at, item.reason, item.last_reviewed_at = s.due_at, s.reason, now


def queue(db: Session, student_id: uuid.UUID, *, horizon_days: int = 7) -> dict:
    now = datetime.now(UTC)
    items = list(
        db.scalars(
            select(RevisionItem)
            .where(
                RevisionItem.student_id == student_id,
                RevisionItem.due_at <= now + timedelta(days=horizon_days),
            )
            .order_by(RevisionItem.due_at)
        )
    )

    def row(i: RevisionItem) -> dict:
        return {
            "concept_id": i.concept_id,
            "due_at": i.due_at,
            "interval_days": i.interval_days,
            "reason": i.reason,
            "repetitions": i.repetitions,
            "lapses": i.lapses,
            "last_reviewed_at": i.last_reviewed_at,
            "retention_estimate": retention_estimate(i.interval_days, i.last_reviewed_at, now),
        }

    return {
        "due": [row(i) for i in items if i.due_at <= now],
        "upcoming": [row(i) for i in items if i.due_at > now],
    }


def enriched_queue(db: Session, student_id: uuid.UUID, *, horizon_days: int = 7) -> dict:
    """The queue with each item's concept (names, chapter) and current mastery attached."""
    from app.modules.curriculum import service as curriculum
    from app.modules.knowledge_model import service as knowledge

    q = queue(db, student_id, horizon_days=horizon_days)
    items = q["due"] + q["upcoming"]
    ids = [i["concept_id"] for i in items]
    ctx = curriculum.concept_context(db, ids)
    mastery = knowledge.mastery_map(db, student_id, ids)
    for i in items:
        i["concept"] = ctx.get(i["concept_id"])
        i["mastery"] = knowledge.describe(mastery.get(i["concept_id"]))
    return q


def due_concept_ids(db: Session, student_id: uuid.UUID, limit: int = 10) -> list[int]:
    now = datetime.now(UTC)
    return list(
        db.scalars(
            select(RevisionItem.concept_id)
            .where(RevisionItem.student_id == student_id, RevisionItem.due_at <= now)
            .order_by(RevisionItem.due_at)
            .limit(limit)
        )
    )
