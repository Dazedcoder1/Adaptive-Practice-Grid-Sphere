"""Pre-aggregated analytics (design §12, §20). Routed to the `analytics` queue."""

import uuid

from app.config.database import SessionLocal
from app.shared.events import already_processed, mark_processed
from app.workers.celery_app import ReliableTask, celery_app

CONSUMER = "analytics"


@celery_app.task(name="app.workers.analytics.on_question_answered", base=ReliableTask)
def on_question_answered(event_id: str, payload: dict) -> None:
    eid = uuid.UUID(event_id)
    with SessionLocal() as db, db.begin():
        if already_processed(db, CONSUMER, eid):
            return
        # TODO(analytics): update daily per-student / per-concept aggregates
        mark_processed(db, CONSUMER, eid)


@celery_app.task(name="app.workers.analytics.on_test_completed", base=ReliableTask)
def on_test_completed(event_id: str, payload: dict) -> None:
    pass
