import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    email: str
    display_name: str
    timezone: str
    is_minor: bool
    guardian_email: str | None
    onboarding_completed: bool
    study_mode: str | None
    deletion_requested_at: datetime | None
    created_at: datetime
    curriculum_id: int | None = None
    curriculum_name: str | None = None
    subject_ids: list[int] = []
    goals: list[str] = []
    target_exam_date: date | None = None
    weekly_days: int | None = None
    minutes_per_day: int | None = None


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    timezone: str | None = Field(default=None, max_length=64)


class DeletionStatus(BaseModel):
    deletion_requested_at: datetime | None
    message: str


class Onboarding(BaseModel):
    study_mode: str = Field(pattern="^(school|jee|neet)$")
    curriculum_id: int
    subject_ids: list[int] = Field(min_length=1, max_length=20)
    goals: list[str] = Field(default_factory=list, max_length=5)
    target_exam_date: date | None = None
    weekly_days: int | None = Field(default=None, ge=1, le=7)
    minutes_per_day: int | None = Field(default=None, ge=10, le=600)
