"""Revision scheduling / spaced repetition (design §16.4)."""

import uuid

from app.config.database import SessionLocal
from app.shared.events import already_processed, mark_processed
from app.workers.celery_app import ReliableTask, celery_app

CONSUMER = "revision"


@celery_app.task(name="app.workers.revision.on_question_answered", base=ReliableTask)
def on_question_answered(event_id: str, payload: dict) -> None:
    eid = uuid.UUID(event_id)
    with SessionLocal() as db, db.begin():
        if already_processed(db, CONSUMER, eid):
            return
        # TODO(revision): create/update revision_items, error_notebook on incorrect answers
        mark_processed(db, CONSUMER, eid)


@celery_app.task(name="app.workers.revision.mark_due")
def mark_due() -> None:
    # TODO(revision): find revision_items with due_at <= now and emit RevisionDue
    pass
