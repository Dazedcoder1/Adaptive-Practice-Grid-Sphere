"""Error notebook: questions a student got wrong (added automatically) or saved as difficult."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class MistakeCategory(StrEnum):
    UNCATEGORISED = "uncategorised"
    CONCEPT = "concept"  # didn't understand the idea
    CALCULATION = "calculation"
    MISREAD = "misread"  # misread the question
    TIME = "time"  # ran out of time / rushed
    GUESS = "guess"


class EntryStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"


def _enum(e, name):
    return Enum(e, name=name, values_callable=lambda x: [m.value for m in x])


def _now() -> datetime:
    return datetime.now(UTC)


class ErrorNotebookEntry(Base):
    __tablename__ = "error_notebook_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(16), nullable=False)  # mistake | saved
    category: Mapped[MistakeCategory] = mapped_column(
        _enum(MistakeCategory, "mistake_category"),
        default=MistakeCategory.UNCATEGORISED,
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(String(1000))
    status: Mapped[EntryStatus] = mapped_column(
        _enum(EntryStatus, "notebook_status"), default=EntryStatus.OPEN, nullable=False
    )
    times_wrong: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    times_right_since: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("question_attempts.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("student_id", "question_id"),
        Index("ix_notebook_student_status", "student_id", "status"),
    )
