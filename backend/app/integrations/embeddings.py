"""Embedding provider boundary for the RAG pipeline (design §8.2).

Vectors live in PostgreSQL (pgvector) with a fixed width of DIMENSIONS. Every provider is
asked for that width (OpenAI `dimensions`, Gemini `outputDimensionality`) and vectors are
L2-normalised, so cosine distance behaves the same whichever model produced them. Each
chunk records the model that embedded it; retrieval only compares vectors from the
current model, and changing the model means re-embedding (Admin → AI → Documents).

Providers (EMBEDDING_PROVIDER): openai · gemini · openai_compatible. `fake` (tests only)
is a feature-hashing bag of words — enough for shared words to land close together.
"""

import hashlib
import math
import re
import time
from dataclasses import dataclass

from app.config.settings import settings
from app.integrations.llm import LLMError, http_json

DIMENSIONS = 768
BATCH = 64

PROVIDERS: dict[str, dict[str, str]] = {
    "openai": {
        "label": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "model": "text-embedding-3-small",
    },
    "gemini": {
        "label": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "model": "gemini-embedding-001",
    },
    "openai_compatible": {"label": "OpenAI-compatible", "base_url": "", "model": ""},
}


@dataclass
class EmbedResult:
    vectors: list[list[float]]
    input_tokens: int
    latency_ms: int


def _normalise(v: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


class Embedder:
    def __init__(self, name: str, model: str, key: str, base_url: str):
        self.name, self.model, self.key, self.base_url = name, model, key, base_url.rstrip("/")

    @property
    def model_id(self) -> str:
        """Stored with each vector, so vectors from different models are never compared."""
        return f"{self.name}:{self.model}:{DIMENSIONS}"

    def embed(self, texts: list[str], *, kind: str = "document") -> EmbedResult:
        started = time.perf_counter()
        vectors: list[list[float]] = []
        tokens = 0
        for i in range(0, len(texts), BATCH):
            batch = texts[i : i + BATCH]
            vs, t = self._call(batch, kind)
            if len(vs) != len(batch) or any(len(v) != DIMENSIONS for v in vs):
                raise LLMError(
                    "bad_dimensions",
                    f"The embedding model must return {DIMENSIONS}-dimension vectors.",
                )
            vectors += [_normalise(v) for v in vs]
            tokens += t
        return EmbedResult(vectors, tokens, int((time.perf_counter() - started) * 1000))

    def _call(self, batch: list[str], kind: str) -> tuple[list[list[float]], int]:
        timeout = settings.llm_timeout_seconds
        if self.name == "gemini":
            task = "RETRIEVAL_QUERY" if kind == "query" else "RETRIEVAL_DOCUMENT"
            data = http_json(
                f"{self.base_url}/models/{self.model}:batchEmbedContents",
                headers={"x-goog-api-key": self.key},
                body={
                    "requests": [
                        {
                            "model": f"models/{self.model}",
                            "content": {"parts": [{"text": t}]},
                            "taskType": task,
                            "outputDimensionality": DIMENSIONS,
                        }
                        for t in batch
                    ]
                },
                timeout=timeout,
            )
            try:
                vs = [e["values"] for e in data["embeddings"]]
            except (KeyError, TypeError) as e:
                raise LLMError("bad_response", "Unexpected embedding response.") from e
            return vs, sum(len(t) for t in batch) // 4  # Gemini doesn't report tokens here
        data = http_json(
            f"{self.base_url}/embeddings",
            headers={"Authorization": f"Bearer {self.key}"},
            body={"model": self.model, "input": batch, "dimensions": DIMENSIONS},
            timeout=timeout,
        )
        try:
            rows = sorted(data["data"], key=lambda r: r.get("index", 0))
            vs = [r["embedding"] for r in rows]
        except (KeyError, TypeError) as e:
            raise LLMError("bad_response", "Unexpected embedding response.") from e
        return vs, int((data.get("usage") or {}).get("prompt_tokens") or 0)


class FakeEmbedder(Embedder):
    def __init__(self):
        super().__init__("fake", "hash-bow", "", "")

    def _call(self, batch, kind):
        out = []
        for t in batch:
            v = [0.0] * DIMENSIONS
            for w in re.findall(r"[a-z]{3,}", t.lower()):
                h = int(hashlib.md5(w.encode()).hexdigest(), 16)
                v[h % DIMENSIONS] += 1.0 if (h >> 12) & 1 else -1.0
            if not any(v):
                v[0] = 1.0
            out.append(v)
        return out, sum(len(t) for t in batch) // 4


def get_embedder() -> Embedder | None:
    name = settings.embedding_provider.strip().lower()
    if not name:
        return None
    if name == "fake":
        return FakeEmbedder() if settings.environment == "test" else None
    preset = PROVIDERS.get(name)
    if preset is None:
        return None
    key = settings.embedding_api_key or (
        settings.llm_api_key if name == settings.llm_provider.strip().lower() else ""
    )
    base = settings.embedding_base_url or preset["base_url"]
    model = settings.embedding_model or preset["model"]
    if not key or not base or not model:
        return None
    return Embedder(name, model, key, base)


def status() -> dict | None:
    name = settings.embedding_provider.strip().lower()
    if not name:
        return None
    e = get_embedder()
    return {
        "provider": name,
        "label": PROVIDERS.get(name, {}).get("label", name),
        "model": e.model if e else None,
        "dimensions": DIMENSIONS,
        "ready": e is not None,
    }
