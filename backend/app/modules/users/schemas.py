import uuid
from datetime import datetime

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


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    timezone: str | None = Field(default=None, max_length=64)


class DeletionStatus(BaseModel):
    deletion_requested_at: datetime | None
    message: str
