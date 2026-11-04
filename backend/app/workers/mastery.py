"""Celery entry point for knowledge-model updates (logic lives in knowledge_model.service)."""

import uuid

from app.shared.consumers import run_consumer
from app.workers.celery_app import ReliableTask, celery_app


@celery_app.task(name="app.workers.mastery.on_question_answered", base=ReliableTask)
def on_question_answered(event_id: str, payload: dict) -> None:
    from app.modules.knowledge_model import service

    run_consumer("mastery", service.on_question_answered, uuid.UUID(event_id), payload)
