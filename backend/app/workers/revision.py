"""Celery entry points for revision scheduling (logic lives in revision.service)."""

import uuid

from app.shared.consumers import run_consumer
from app.workers.celery_app import ReliableTask, celery_app


@celery_app.task(name="app.workers.revision.on_question_answered", base=ReliableTask)
def on_question_answered(event_id: str, payload: dict) -> None:
    from app.modules.revision import service

    run_consumer("revision", service.on_question_answered, uuid.UUID(event_id), payload)


@celery_app.task(name="app.workers.revision.mark_due")
def mark_due() -> None:
    """Placeholder for revision reminders (notifications module, later phase)."""
