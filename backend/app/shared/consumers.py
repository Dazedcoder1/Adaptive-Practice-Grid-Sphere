"""Run event consumers exactly once each, whether called by a Celery worker or inline.

Each consumer's effects and its `processed_events` row commit in ONE transaction, and that
row's primary key is (consumer, event_id) — so a redelivery, or a worker and the inline
path racing on the same event, can never apply an effect twice.
"""

import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config.database import SessionLocal
from app.shared.events import OutboxEvent, already_processed, mark_processed

log = logging.getLogger(__name__)

Handler = Callable[[Session, uuid.UUID, dict], None]


def run_consumer(name: str, handler: Handler, event_id: uuid.UUID, payload: dict) -> bool:
    """Returns True if this call applied the effect, False if it had already been applied."""
    try:
        with SessionLocal() as db, db.begin():
            if already_processed(db, name, event_id):
                return False
            handler(db, event_id, payload)
            mark_processed(db, name, event_id)
        return True
    except IntegrityError:
        # Another process committed the same (consumer, event) first — that's fine.
        log.info("consumer %s already handled %s concurrently", name, event_id)
        return False


def process_inline(event_ids: list[uuid.UUID]) -> None:
    """Development convenience (PROCESS_EVENTS_INLINE=true): handle events in-process right
    after commit, then mark them published so the outbox relay skips them. Failures are
    logged and the event is left for the relay/worker to retry — never lost."""
    from app.workers.registry import handlers_for

    for eid in event_ids:
        with SessionLocal() as db:
            ev = db.get(OutboxEvent, eid)
            if ev is None or ev.published_at is not None:
                continue
            etype, payload = ev.event_type, ev.payload
        ok = True
        for name, handler in handlers_for(etype):
            try:
                run_consumer(name, handler, eid, payload)
            except Exception:  # noqa: BLE001
                ok = False
                log.exception("inline consumer %s failed for %s; left for the worker", name, eid)
        if ok:
            with SessionLocal() as db, db.begin():
                ev = db.scalar(select(OutboxEvent).where(OutboxEvent.id == eid).with_for_update())
                if ev and ev.published_at is None:
                    ev.published_at = datetime.now(UTC)
