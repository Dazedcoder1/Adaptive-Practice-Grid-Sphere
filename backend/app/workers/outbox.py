"""Outbox relay: moves committed outbox rows onto the task queue (design §10).

Runs every couple of seconds from beat. Uses SKIP LOCKED so several relays can run
safely. If publishing fails the row stays unpublished and is retried next tick.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import select

from app.config.database import SessionLocal
from app.shared.events import EventType, OutboxEvent
from app.workers.celery_app import celery_app

log = logging.getLogger(__name__)

# event type -> consumer task names (each consumer must be idempotent)
CONSUMERS: dict[str, list[str]] = {
    EventType.QUESTION_ANSWERED: [
        "app.workers.mastery.on_question_answered",
        "app.workers.revision.on_question_answered",
        "app.workers.analytics.on_question_answered",
    ],
    EventType.TEST_COMPLETED: ["app.workers.analytics.on_test_completed"],
}

BATCH = 100
MAX_PUBLISH_ATTEMPTS = 10


@celery_app.task(name="app.workers.outbox.relay")
def relay() -> int:
    published = 0
    with SessionLocal() as db, db.begin():
        rows = db.scalars(
            select(OutboxEvent)
            .where(OutboxEvent.published_at.is_(None), OutboxEvent.dead_lettered_at.is_(None))
            .order_by(OutboxEvent.created_at)
            .limit(BATCH)
            .with_for_update(skip_locked=True)
        ).all()
        for ev in rows:
            try:
                for task_name in CONSUMERS.get(ev.event_type, []):
                    celery_app.send_task(task_name, args=[str(ev.id), ev.payload])
                ev.published_at = datetime.now(UTC)
                published += 1
            except Exception as e:  # noqa: BLE001
                ev.attempts += 1
                ev.last_error = repr(e)[:2000]
                if ev.attempts >= MAX_PUBLISH_ATTEMPTS:
                    ev.dead_lettered_at = datetime.now(UTC)
                log.exception("outbox publish failed for %s", ev.id)
    return published
