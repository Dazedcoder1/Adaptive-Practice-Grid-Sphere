"""Request schemas for the AI tutor and AI administration."""

import uuid
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

Mode = Literal["teach", "hint", "solve", "test", "mistake"]


class ChatIn(BaseModel):
    mode: Mode
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: uuid.UUID | None = None
    concept_id: int | None = None
    session_question_id: uuid.UUID | None = None


class QuestionHelpIn(BaseModel):
    session_question_id: uuid.UUID
    conversation_id: uuid.UUID | None = None


class FeedbackIn(BaseModel):
    helpful: bool | None


class AiSettingsIn(BaseModel):
    tutor_enabled: bool
    chat_model: str = Field(default="", max_length=120)
    fallback_model: str = Field(default="", max_length=120)
    temperature: float = Field(ge=0, le=1.5)
    max_output_tokens: int = Field(ge=100, le=8000)
    student_daily_messages: int = Field(ge=0, le=1000)
    student_daily_tokens: int = Field(ge=0, le=10_000_000)
    platform_daily_cost_usd: Decimal = Field(ge=0, le=100_000)
    input_price_per_mtok: Decimal = Field(ge=0, le=1000)
    output_price_per_mtok: Decimal = Field(ge=0, le=1000)
    embedding_price_per_mtok: Decimal = Field(ge=0, le=1000)
    retrieval_top_k: int = Field(ge=1, le=10)
    min_similarity: float = Field(ge=0, le=1)
    chunk_target_tokens: int = Field(ge=80, le=1500)
    chunk_overlap_tokens: int = Field(ge=0, le=400)
    conversation_retention_days: int = Field(ge=7, le=3650)


class PromptIn(BaseModel):
    body: str = Field(min_length=20, max_length=6000)
    note: str = Field(default="", max_length=300)


class TestIn(BaseModel):
    kind: Literal["chat", "embedding"]
