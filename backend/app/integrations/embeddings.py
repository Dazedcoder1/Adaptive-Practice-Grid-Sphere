"""Embedding provider boundary for the RAG pipeline (design §8.2).

Vectors are stored in PostgreSQL with pgvector initially. Enable it once with a
migration: `op.execute("CREATE EXTENSION IF NOT EXISTS vector")` (Neon supports it).
"""

from typing import Protocol

from app.config.settings import settings


class Embedder(Protocol):
    dimensions: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class NotConfiguredEmbedder:
    dimensions = 0

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("No embedding model configured — set EMBEDDING_MODEL in .env")


def get_embedder() -> Embedder:
    if not settings.embedding_model:
        return NotConfiguredEmbedder()
    raise NotImplementedError(f"Embedding model {settings.embedding_model!r} not wired up yet")
