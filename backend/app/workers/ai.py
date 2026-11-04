"""AI queue tasks (worker-ai): embedding study material and privacy clean-up."""

import uuid

from app.config.database import SessionLocal, transaction
from app.workers.celery_app import ReliableTask, celery_app


@celery_app.task(name="ai.embed_document", base=ReliableTask)
def embed_document(doc_id: str) -> int:
    from app.modules.rag import service

    with SessionLocal() as db, transaction(db):
        return service.embed_document(db, uuid.UUID(doc_id))


@celery_app.task(name="ai.purge_conversations")
def purge_conversations() -> int:
    """Delete tutor conversations older than the retention period set in Admin → AI."""
    from app.modules.ai_tutor import service

    with SessionLocal() as db, transaction(db):
        return service.purge_expired(db)
