"""Question bank with immutable versions and an approval lifecycle.

- `questions` is the stable identity; `question_versions` hold the content.
- A version can be edited only while it's a DRAFT. Once submitted, approved or published it
  is never modified: editing a published question creates a new draft version, and the old
  published version keeps being served until the new one is published.
- Attempts reference the exact version a student saw, so edits never rewrite history.
- Answer keys live only in `answer` and never reach student-facing endpoints.
"""

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base, TimestampMixin


class QuestionType(StrEnum):
    MCQ_SINGLE = "mcq_single"
    MCQ_MULTI = "mcq_multi"
    NUMERICAL = "numerical"
    INTEGER = "integer"
    FILL_BLANK = "fill_blank"
    MATCH = "match"
    ASSERTION_REASON = "assertion_reason"
    SUBJECTIVE = "subjective"
    DIAGRAM = "diagram"  # single-correct MCQ built around an image


class VersionStatus(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    PUBLISHED = "published"
    SUPERSEDED = "superseded"  # was published, replaced by a newer version
    REJECTED = "rejected"
    ARCHIVED = "archived"


def _enum(e, name):
    return Enum(e, name=name, values_callable=lambda x: [m.value for m in x])


def _now() -> datetime:
    return datetime.now(UTC)


class Question(TimestampMixin, Base):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # The version students are served. NULL until first publication.
    published_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("question_versions.id", use_alter=True, name="fk_questions_published_version")
    )
    latest_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("question_versions.id", use_alter=True, name="fk_questions_latest_version")
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    is_sample: Mapped[bool] = mapped_column(default=False, nullable=False)

    concepts: Mapped[list["QuestionConcept"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )


class QuestionVersion(Base):
    __tablename__ = "question_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[VersionStatus] = mapped_column(
        _enum(VersionStatus, "question_version_status"),
        default=VersionStatus.DRAFT,
        nullable=False,
    )
    type: Mapped[QuestionType] = mapped_column(_enum(QuestionType, "question_type"), nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 recall … 5 olympiad
    stem: Mapped[str] = mapped_column(Text, nullable=False)  # markdown + maths
    # Student-safe payload: options, match columns, image key, unit … — never answers.
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    # Server-only answer key and evaluation rules.
    answer: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    solution: Mapped[str] = mapped_column(Text, default="", nullable=False)
    hints: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    estimated_seconds: Mapped[int] = mapped_column(Integer, default=90, nullable=False)
    source: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_note: Mapped[str | None] = mapped_column(String(1000))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("question_id", "version"),
        CheckConstraint("difficulty BETWEEN 1 AND 5", name="difficulty_range"),
        Index("ix_question_versions_status", "status"),
    )


class QuestionConcept(Base):
    __tablename__ = "question_concepts"

    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True
    )
    concept_id: Mapped[int] = mapped_column(
        ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    __table_args__ = (CheckConstraint("weight > 0 AND weight <= 1", name="weight_range"),)
