"""Celery app (design §10, §13). Queues map to compose services:
default → worker-default, ai → worker-ai, analytics → worker-analytics; beat → scheduler."""

from celery import Celery, Task
from kombu import Exchange, Queue

from app.config.settings import settings

celery_app = Celery(
    "adaptive_practice",
    broker=settings.broker_url,
    backend=settings.result_backend,
    include=[
        "app.workers.outbox",
        "app.workers.attempt",
        "app.workers.mastery",
        "app.workers.revision",
        "app.workers.notebook",
        "app.workers.analytics",
        "app.workers.ai",
    ],
)

celery_app.conf.update(
    task_default_queue="default",
    task_queues=tuple(
        Queue(q, Exchange(q, type="direct"), routing_key=q) for q in ("default", "ai", "analytics")
    ),
    task_default_exchange="default",
    task_default_routing_key="default",
    task_routes={
        "app.workers.analytics.*": {"queue": "analytics"},
        "ai.*": {"queue": "ai"},
    },
    task_acks_late=True,  # re-deliver if a worker dies mid-task
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    beat_schedule={
        "outbox-relay": {"task": "app.workers.outbox.relay", "schedule": 2.0},
        "revision-daily-due": {"task": "app.workers.revision.mark_due", "schedule": 3600.0},
        "ai-purge-conversations": {"task": "ai.purge_conversations", "schedule": 86400.0},
    },
)


class ReliableTask(Task):
    """Base for event consumers: exponential-backoff retries, then a dead-letter row.

    Consumers must be idempotent (see app.shared.events.already_processed), so a retry
    after a partial failure is safe.
    """

    autoretry_for = (Exception,)
    retry_backoff = True
    retry_backoff_max = 300
    retry_jitter = True
    max_retries = 5

    def on_failure(self, exc, task_id, args, kwargs, einfo):  # called once retries are exhausted
        import uuid

        from app.config.database import SessionLocal
        from app.shared.events import DeadLetter

        event_id = None
        if args:
            try:
                event_id = uuid.UUID(str(args[0]))
            except ValueError:
                event_id = None
        with SessionLocal() as db, db.begin():
            db.add(
                DeadLetter(
                    task_name=self.name,
                    event_id=event_id,
                    args=list(args),
                    error=f"{type(exc).__name__}: {exc}"[:4000],
                )
            )
