"""Study material for retrieval (design §8.2). Other modules must not write these tables.

- `rag_documents`: one uploaded source with its academic metadata, licence and review
  status. Only APPROVED documents are ever retrieved for students.
- `rag_chunks`: passages cut from a document, each mapped to chapter/concepts, with a
  generated full-text vector (keyword search) and an optional pgvector embedding.
- `rag_eval_cases` / `rag_eval_runs`: queries with a known right source, to measure
  retrieval quality (hit rate, MRR) when content, chunking or the model changes.
"""

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Computed,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base, TimestampMixin
from app.integrations.embeddings import DIMENSIONS


class SourceType(StrEnum):
    NOTES = "notes"  # study notes written for the platform
    TEXTBOOK = "textbook"
    REFERENCE = "reference"
    SOLUTIONS = "solutions"


class Licence(StrEnum):
    OWNED = "owned"  # written by us
    LICENSED = "licensed"  # used under an agreement
    OPEN = "open"  # openly licensed (e.g. CC BY)
    UNKNOWN = "unknown"  # can't be approved until cleared


class DocumentStatus(StrEnum):
    PROCESSING = "processing"
    REVIEW = "review"  # extracted and chunked, waiting for approval
    APPROVED = "approved"  # retrievable for students
    FAILED = "failed"
    ARCHIVED = "archived"


def _enum(e, name):
    return Enum(e, name=name, values_callable=lambda x: [m.value for m in x])


def _now() -> datetime:
    return datetime.now(UTC)


class RagDocument(TimestampMixin, Base):
    __tablename__ = "rag_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    source_type: Mapped[SourceType] = mapped_column(
        _enum(SourceType, "rag_source_type"), nullable=False
    )
    licence: Mapped[Licence] = mapped_column(_enum(Licence, "rag_licence"), nullable=False)
    licence_note: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    curriculum_id: Mapped[int] = mapped_column(
        ForeignKey("curricula.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False
    )
    chapter_id: Mapped[int | None] = mapped_column(ForeignKey("chapters.id", ondelete="SET NULL"))
    status: Mapped[DocumentStatus] = mapped_column(
        _enum(DocumentStatus, "rag_document_status"),
        default=DocumentStatus.PROCESSING,
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # A re-upload of an existing document; approving it archives the one it replaces.
    replaces_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("rag_documents.id", ondelete="SET NULL")
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    storage_key: Mapped[str | None] = mapped_column(String(300))  # original file in R2
    text: Mapped[str] = mapped_column(Text, default="", nullable=False)  # normalised text
    page_count: Mapped[int | None] = mapped_column(Integer)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    embedded_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    embedding_error: Mapped[str | None] = mapped_column(String(300))
    error: Mapped[str | None] = mapped_column(String(500))
    is_sample: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("ix_rag_documents_scope", "curriculum_id", "subject_id", "status"),)


class RagChunk(Base):
    __tablename__ = "rag_chunks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rag_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    heading: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    page: Mapped[int | None] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    chapter_id: Mapped[int | None] = mapped_column(ForeignKey("chapters.id", ondelete="SET NULL"))
    concept_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), default=list, nullable=False)
    concepts_edited: Mapped[bool] = mapped_column(default=False, nullable=False)
    search: Mapped[Any] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('english', coalesce(heading, '') || ' ' || text)", persisted=True),
    )
    embedding: Mapped[list[float] | None] = mapped_column(Vector(DIMENSIONS))
    embedding_model: Mapped[str | None] = mapped_column(String(160))

    __table_args__ = (
        Index("ix_rag_chunks_search", "search", postgresql_using="gin"),
        Index("ix_rag_chunks_concepts", "concept_ids", postgresql_using="gin"),
        Index(
            "ix_rag_chunks_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


class RagEvalCase(Base):
    __tablename__ = "rag_eval_cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query: Mapped[str] = mapped_column(String(500), nullable=False)
    curriculum_id: Mapped[int] = mapped_column(
        ForeignKey("curricula.id", ondelete="CASCADE"), nullable=False
    )
    subject_id: Mapped[int | None] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"))
    expected_document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rag_documents.id", ondelete="CASCADE"), nullable=False
    )
    # Optional phrase the right passage must contain (more precise than the document).
    expected_phrase: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )


class RagEvalRun(Base):
    __tablename__ = "rag_eval_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    k: Mapped[int] = mapped_column(Integer, nullable=False)
    retrieval: Mapped[str] = mapped_column(String(32), nullable=False)  # hybrid | keyword
    cases: Mapped[int] = mapped_column(Integer, nullable=False)
    hit_rate: Mapped[float] = mapped_column(Float, nullable=False)
    mrr: Mapped[float] = mapped_column(Float, nullable=False)
    results: Mapped[list[dict]] = mapped_column(JSONB, default=list, nullable=False)
    run_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
