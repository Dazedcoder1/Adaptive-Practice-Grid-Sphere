"""Celery entry point for the error notebook (logic lives in error_notebook.service)."""

import uuid

from app.shared.consumers import run_consumer
from app.workers.celery_app import ReliableTask, celery_app


@celery_app.task(name="app.workers.notebook.on_question_answered", base=ReliableTask)
def on_question_answered(event_id: str, payload: dict) -> None:
    from app.modules.error_notebook import service

    run_consumer("error_notebook", service.on_question_answered, uuid.UUID(event_id), payload)
