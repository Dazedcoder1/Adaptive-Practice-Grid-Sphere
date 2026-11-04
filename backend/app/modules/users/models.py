"""Student profile tables. Other modules must not write these tables directly."""

import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base, TimestampMixin


class StudentProfile(TimestampMixin, Base):
    __tablename__ = "student_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata", nullable=False)
    # Only what's needed to decide whether guardian consent applies — no date of birth.
    is_minor: Mapped[bool] = mapped_column(Boolean, nullable=False)
    guardian_email: Mapped[str | None] = mapped_column(String(320))
    # Onboarding: study mode, board/exam + class (= curriculum), subjects, goals, schedule.
    # `preferences` holds {"subject_ids": [...], "goals": [...], "schedule": {...}}.
    curriculum_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("curricula.id", ondelete="SET NULL")
    )
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    study_mode: Mapped[str | None] = mapped_column(String(16))  # school | jee | neet
    preferences: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    target_exam_date: Mapped[date | None] = mapped_column(Date)
