import uuid
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.modules.practice.models import SessionMode


class CreateSession(BaseModel):
    mode: SessionMode = SessionMode.ADAPTIVE
    subject_id: int | None = None
    chapter_id: int | None = None
    topic_id: int | None = None
    concept_ids: list[int] | None = Field(default=None, max_length=50)
    question_ids: list[uuid.UUID] | None = Field(default=None, max_length=30)
    count: int | None = Field(default=None, ge=1, le=30)

    @model_validator(mode="after")
    def _scope(self):
        if self.mode == SessionMode.REVIEW and not self.question_ids:
            raise ValueError("Review sessions need question_ids.")
        if self.mode not in (SessionMode.REVIEW, SessionMode.REVISION) and not any(
            [self.subject_id, self.chapter_id, self.topic_id, self.concept_ids]
        ):
            raise ValueError("Choose a subject, chapter, topic or concepts.")
        return self


class SubmitAnswer(BaseModel):
    session_question_id: uuid.UUID
    response: dict[str, Any]
