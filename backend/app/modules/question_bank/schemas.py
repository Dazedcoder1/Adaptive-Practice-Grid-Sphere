import uuid
from typing import Any

from pydantic import BaseModel, Field

from app.modules.question_bank.models import QuestionType


class ConceptTag(BaseModel):
    concept_id: int
    weight: float = Field(default=1.0, gt=0, le=1)


class QuestionIn(BaseModel):
    type: QuestionType
    difficulty: int = Field(ge=1, le=5)
    stem: str = Field(min_length=1, max_length=20000)
    content: dict[str, Any] = Field(default_factory=dict)
    answer: dict[str, Any] = Field(default_factory=dict)
    solution: str = Field(default="", max_length=20000)
    hints: list[str] = Field(default_factory=list, max_length=5)
    estimated_seconds: int = Field(default=90, ge=10, le=3600)
    source: str | None = Field(default=None, max_length=200)
    concepts: list[ConceptTag] = Field(min_length=1, max_length=10)


class ReviewNote(BaseModel):
    note: str | None = Field(default=None, max_length=1000)


class RejectNote(BaseModel):
    note: str = Field(min_length=3, max_length=1000)


class ImportQuestions(BaseModel):
    questions: list[QuestionIn] = Field(min_length=1, max_length=500)
    publish: bool = False


class ImportResult(BaseModel):
    created: list[uuid.UUID]
    published: bool
