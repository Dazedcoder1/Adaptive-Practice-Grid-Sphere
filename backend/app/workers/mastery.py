"""Knowledge-model updates from attempt evidence (design §6, §16.2). BKT goes here."""

import uuid

from app.config.database import SessionLocal
from app.shared.events import already_processed, mark_processed
from app.workers.celery_app import ReliableTask, celery_app

CONSUMER = "mastery"


@celery_app.task(name="app.workers.mastery.on_question_answered", base=ReliableTask)
def on_question_answered(event_id: str, payload: dict) -> None:
    eid = uuid.UUID(event_id)
    with SessionLocal() as db, db.begin():
        if already_processed(db, CONSUMER, eid):
            return
        # TODO(knowledge_model): update student_mastery + mastery_history (Phase 1)
        mark_processed(db, CONSUMER, eid)
