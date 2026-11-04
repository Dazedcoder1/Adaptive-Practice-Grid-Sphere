"""Transactional outbox (design §7.2, §10).

A domain change and its event are written in the SAME database transaction, so an
acknowledged answer is never lost if Redis or a worker is down. The outbox relay
(app/workers/outbox.py) publishes pending rows to Celery; consumers record what they've
handled in `processed_events` so redelivery is harmless (idempotent consumers).
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, func, select
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.config.database import Base


class EventType(StrEnum):
    STUDENT_REGISTERED = "StudentRegistered"
    DIAGNOSTIC_COMPLETED = "DiagnosticCompleted"
    PRACTICE_STARTED = "PracticeStarted"
    QUESTION_ANSWERED = "QuestionAnswered"
    MASTERY_UPDATED = "MasteryUpdated"
    CONCEPT_MASTERED = "ConceptMastered"
    REVISION_DUE = "RevisionDue"
    TEST_COMPLETED = "TestCompleted"
    ACHIEVEMENT_UNLOCKED = "AchievementUnlocked"


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text)
    # Set when publishing failed MAX_PUBLISH_ATTEMPTS times; the relay stops retrying it.
    dead_lettered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DeadLetter(Base):
    """A consumer task that exhausted its retries. Kept for inspection and manual replay."""

    __tablename__ = "dead_letters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_name: Mapped[str] = mapped_column(String(128), nullable=False)
    event_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    args: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    error: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    replayed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProcessedEvent(Base):
    """One row per (consumer, event) — makes every consumer idempotent."""

    __tablename__ = "processed_events"

    consumer: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


def emit(
    db: Session,
    event_type: EventType,
    aggregate_type: str,
    aggregate_id: str | uuid.UUID,
    payload: dict[str, Any],
) -> OutboxEvent:
    """Stage an event in the caller's transaction. The caller commits."""
    event = OutboxEvent(
        event_type=str(event_type),
        aggregate_type=aggregate_type,
        aggregate_id=str(aggregate_id),
        payload=payload,
    )
    db.add(event)
    return event


def already_processed(db: Session, consumer: str, event_id: uuid.UUID) -> bool:
    return (
        db.scalar(
            select(ProcessedEvent).where(
                ProcessedEvent.consumer == consumer, ProcessedEvent.event_id == event_id
            )
        )
        is not None
    )


def mark_processed(db: Session, consumer: str, event_id: uuid.UUID) -> None:
    db.add(ProcessedEvent(consumer=consumer, event_id=event_id))
