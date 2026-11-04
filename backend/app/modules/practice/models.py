"""Practice sessions and question attempts.

`question_attempts` is an immutable history: rows are inserted once and never updated.
The submitted response is stored separately from its evaluation, and every attempt records
the exact question version and the difficulty it was delivered at.
"""

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class SessionMode(StrEnum):
    ADAPTIVE = "adaptive"  # dynamic selection from the knowledge state
    DIAGNOSTIC = "diagnostic"  # one question per concept to estimate a starting point
    TOPIC = "topic"  # student-chosen scope, difficulty still adapts
    REVISION = "revision"  # due revision concepts
    REVIEW = "review"  # re-attempt specific questions (error notebook)


class SessionStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class Evaluation(StrEnum):
    CORRECT = "correct"
    PARTIAL = "partial"
    INCORRECT = "incorrect"
    UNGRADED = "ungraded"  # subjective answers: stored, not auto-marked


def _enum(e, name):
    return Enum(e, name=name, values_callable=lambda x: [m.value for m in x])


def _now() -> datetime:
    return datetime.now(UTC)


class PracticeSession(Base):
    __tablename__ = "practice_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    mode: Mapped[SessionMode] = mapped_column(_enum(SessionMode, "session_mode"), nullable=False)
    status: Mapped[SessionStatus] = mapped_column(
        _enum(SessionStatus, "session_status"), default=SessionStatus.ACTIVE, nullable=False
    )
    # Scope snapshot at creation: {"subject_id", "chapter_id", "concept_ids": [...],
    # "question_ids": [...] (review mode)}
    scope: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    target_count: Mapped[int] = mapped_column(Integer, nullable=False)
    answered_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_sessions_student_status", "student_id", "status"),
        Index("ix_sessions_student_created", "student_id", "created_at"),
    )


class SessionQuestion(Base):
    """A question delivered in a session, with the adaptive decision that chose it."""

    __tablename__ = "session_questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("practice_sessions.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("questions.id"), nullable=False)
    question_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("question_versions.id"), nullable=False
    )
    target_concept_id: Mapped[int | None] = mapped_column(ForeignKey("concepts.id"))
    # Explainable, auditable record of why this question was chosen.
    selection: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    delivered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
    hints_revealed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Hint-style help from the AI tutor before answering. Counts like a hint, so an
    # assisted correct answer is weaker evidence of mastery.
    tutor_assists: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("question_attempts.id", use_alter=True, name="fk_session_questions_attempt")
    )

    __table_args__ = (UniqueConstraint("session_id", "position"),)


class QuestionAttempt(Base):
    __tablename__ = "question_attempts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("practice_sessions.id", ondelete="CASCADE"), nullable=False
    )
    session_question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("session_questions.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("questions.id"), nullable=False)
    question_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("question_versions.id"), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(String(80), nullable=False)
    response: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)  # as submitted
    evaluation: Mapped[Evaluation] = mapped_column(_enum(Evaluation, "evaluation"), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)  # 0..1
    time_taken_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    hints_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    difficulty_at_delivery: Mapped[int] = mapped_column(Integer, nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)  # for this question
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("student_id", "idempotency_key"),
        Index("ix_attempt_student_created", "student_id", "created_at"),
        Index("ix_attempt_student_question", "student_id", "question_id"),
    )
