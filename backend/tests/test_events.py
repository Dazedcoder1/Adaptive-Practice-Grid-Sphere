"""Outbox relay, idempotent consumers and dead-lettering."""

import uuid

import pytest
from sqlalchemy import func, select

from app.config.database import transaction
from app.shared.events import DeadLetter, EventType, OutboxEvent, ProcessedEvent, emit
from app.workers import outbox
from app.workers.celery_app import celery_app


@pytest.fixture
def sent(monkeypatch):
    celery_app.loader.import_default_modules()
    calls: list[str] = []

    def fake_send(name, args):
        calls.append(name)
        celery_app.tasks[name].apply(args=args, throw=True)

    monkeypatch.setattr(celery_app, "send_task", fake_send)
    return calls


def _emit(db) -> uuid.UUID:
    with transaction(db):
        ev = emit(db, EventType.QUESTION_ANSWERED, "attempt", "a1", {"concept_ids": [1]})
    return ev.id


def test_event_is_not_visible_if_the_business_transaction_rolls_back(db):
    with pytest.raises(RuntimeError), transaction(db):
        emit(db, EventType.QUESTION_ANSWERED, "attempt", "a1", {})
        raise RuntimeError("attempt insert failed")
    assert db.scalar(select(func.count()).select_from(OutboxEvent)) == 0


def test_relay_fans_out_once_and_consumers_are_idempotent(db, sent):
    event_id = _emit(db)
    assert outbox.relay.apply().get() == 1
    assert sorted(n.split(".")[-2] for n in sent) == ["analytics", "mastery", "revision"]
    assert outbox.relay.apply().get() == 0  # already published

    celery_app.tasks["app.workers.mastery.on_question_answered"].apply(
        args=[str(event_id), {}], throw=True
    )  # redelivery
    assert db.scalar(select(func.count()).select_from(ProcessedEvent)) == 3


def test_publish_failures_retry_then_dead_letter(db, monkeypatch):
    def broken(*a, **k):
        raise ConnectionError("broker down")

    monkeypatch.setattr(celery_app, "send_task", broken)
    event_id = _emit(db)
    for _ in range(outbox.MAX_PUBLISH_ATTEMPTS):
        assert outbox.relay.apply().get() == 0

    db.expire_all()
    ev = db.get(OutboxEvent, event_id)
    assert ev.published_at is None and ev.dead_lettered_at is not None
    assert ev.attempts == outbox.MAX_PUBLISH_ATTEMPTS and "broker down" in ev.last_error


def test_exhausted_consumer_writes_dead_letter(db):
    task = celery_app.tasks["app.workers.mastery.on_question_answered"]
    eid = uuid.uuid4()
    task.on_failure(ValueError("bad payload"), "task-1", (str(eid), {}), {}, None)
    dl = db.scalar(select(DeadLetter))
    assert dl.task_name == task.name and dl.event_id == eid and "bad payload" in dl.error
