"""AI tutor tables (design §8.1, brief §7.7). Other modules must not write these directly.

- `ai_settings`: one row of admin-controlled behaviour (on/off, models, limits, prices,
  retrieval). API keys are never stored here — only in the environment.
- `ai_prompt_versions`: versioned instruction text per prompt key; at most one active
  version per key, otherwise the built-in default in prompts.py is used.
- `tutor_conversations` / `tutor_messages`: a student's own tutor history. Each assistant
  message records how it was produced (AI or study notes), the prompt version, model,
  token counts and the sources it cited.
- `ai_usage`: one row per provider call (tutor, embedding, admin test) for cost and
  reliability monitoring.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


def _now() -> datetime:
    return datetime.now(UTC)


class AiSettings(Base):
    __tablename__ = "ai_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    tutor_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Blank = the model from the environment / provider default.
    chat_model: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    fallback_model: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    temperature: Mapped[float] = mapped_column(Float, default=0.3, nullable=False)
    max_output_tokens: Mapped[int] = mapped_column(Integer, default=900, nullable=False)
    # Limits
    student_daily_messages: Mapped[int] = mapped_column(Integer, default=40, nullable=False)
    student_daily_tokens: Mapped[int] = mapped_column(Integer, default=60000, nullable=False)
    platform_daily_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("5.00"), nullable=False
    )
    # Prices for cost estimates (USD per million tokens) — enter your provider's current rates.
    input_price_per_mtok: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), default=Decimal("0"), nullable=False
    )
    output_price_per_mtok: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), default=Decimal("0"), nullable=False
    )
    embedding_price_per_mtok: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), default=Decimal("0"), nullable=False
    )
    # Retrieval & chunking
    retrieval_top_k: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    min_similarity: Mapped[float] = mapped_column(Float, default=0.3, nullable=False)
    chunk_target_tokens: Mapped[int] = mapped_column(Integer, default=350, nullable=False)
    chunk_overlap_tokens: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    # Privacy: tutor conversations older than this are deleted by the scheduler.
    conversation_retention_days: Mapped[int] = mapped_column(Integer, default=365, nullable=False)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    __table_args__ = (CheckConstraint("id = 1", name="single_row"),)


class PromptVersion(Base):
    __tablename__ = "ai_prompt_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    note: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("key", "version"),
        Index(
            "uq_ai_prompt_versions_one_active",
            "key",
            unique=True,
            postgresql_where=text("is_active"),
        ),
    )


class TutorConversation(Base):
    __tablename__ = "tutor_conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)  # mode it started in
    concept_id: Mapped[int | None] = mapped_column(ForeignKey("concepts.id", ondelete="SET NULL"))
    session_question_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("session_questions.id", ondelete="SET NULL")
    )
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )

    __table_args__ = (Index("ix_tutor_conversations_student", "student_id", "updated_at"),)


class TutorMessage(Base):
    __tablename__ = "tutor_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tutor_conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # student | tutor
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # How a tutor reply was produced: ai | notes (no LLM) | safety | unavailable
    source: Mapped[str | None] = mapped_column(String(16))
    citations: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    # Guardrail outcomes, e.g. answer_withheld, citation_removed, possible_injection
    flags: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    actions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    prompt_versions: Mapped[dict[str, int]] = mapped_column(JSONB, default=dict, nullable=False)
    provider: Mapped[str | None] = mapped_column(String(32))
    model: Mapped[str | None] = mapped_column(String(120))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    helpful: Mapped[bool | None] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )

    __table_args__ = (Index("ix_tutor_messages_conversation", "conversation_id", "created_at"),)


class AiUsage(Base):
    __tablename__ = "ai_usage"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    feature: Mapped[str] = mapped_column(String(32), nullable=False)  # tutor | embedding | test
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(160), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=Decimal("0"), nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ok: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(32))
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )

    __table_args__ = (
        Index("ix_ai_usage_created", "created_at"),
        Index("ix_ai_usage_user_created", "user_id", "created_at"),
    )
