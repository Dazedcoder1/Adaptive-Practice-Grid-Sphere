"""Document ingestion and retrieval (design §8.2).

Approved documents → extraction → normalisation → chapter/concept mapping → chunking →
embeddings → vector index → metadata-filtered retrieval → light reranking → LLM context.

Retrieval applies the curriculum and approval filters *before* any search, so a student can
only ever retrieve approved material from their own syllabus and subjects. Keyword search
(PostgreSQL full text) always runs; vector search joins it when an embedding model is set
up, and the two rankings are fused with reciprocal-rank fusion.
"""

import hashlib
import logging
import math
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.integrations import embeddings, storage
from app.integrations.llm import LLMError
from app.modules.ai_tutor import config as ai_config
from app.modules.curriculum.models import Chapter, Concept, Subject, Topic
from app.modules.rag.chunking import chunk, map_concepts
from app.modules.rag.extraction import ExtractionError, extract
from app.modules.rag.models import (
    DocumentStatus,
    Licence,
    RagChunk,
    RagDocument,
    RagEvalCase,
    RagEvalRun,
    SourceType,
)
from app.shared.exceptions import AppError, Conflict, NotFound

log = logging.getLogger(__name__)
RRF_K = 60


def _now() -> datetime:
    return datetime.now(UTC)


def get_or_404(db: Session, doc_id: uuid.UUID) -> RagDocument:
    doc = db.get(RagDocument, doc_id)
    if doc is None:
        raise NotFound("Document not found.")
    return doc


def _check_scope(db: Session, curriculum_id: int, subject_id: int, chapter_id: int | None):
    subject = db.get(Subject, subject_id)
    if subject is None or subject.curriculum_id != curriculum_id:
        raise AppError("Choose a subject from that curriculum.", code="bad_scope")
    if chapter_id is not None:
        ch = db.get(Chapter, chapter_id)
        if ch is None or ch.subject_id != subject_id:
            raise AppError("Choose a chapter from that subject.", code="bad_scope")


def _concepts_for(db: Session, subject_id: int, chapter_id: int | None) -> list[dict]:
    stmt = (
        select(Concept.id, Concept.code, Concept.name)
        .join(Topic, Topic.id == Concept.topic_id)
        .join(Chapter, Chapter.id == Topic.chapter_id)
        .where(Chapter.subject_id == subject_id)
    )
    if chapter_id is not None:
        stmt = stmt.where(Chapter.id == chapter_id)
    return [{"id": i, "code": c, "name": n} for i, c, n in db.execute(stmt).all()]


def _chapter_of(db: Session, concept_ids: list[int]) -> int | None:
    if not concept_ids:
        return None
    return db.scalar(
        select(Topic.chapter_id)
        .join(Concept, Concept.topic_id == Topic.id)
        .where(Concept.id == concept_ids[0])
    )


# ── ingestion ────────────────────────────────────────────────────────────────


def create_document(
    db: Session,
    *,
    actor: uuid.UUID | None,
    file_name: str,
    data: bytes,
    title: str,
    curriculum_id: int,
    subject_id: int,
    chapter_id: int | None,
    source_type: SourceType,
    licence: Licence,
    licence_note: str = "",
    description: str = "",
    replaces_id: uuid.UUID | None = None,
    is_sample: bool = False,
) -> RagDocument:
    if len(data) > settings.rag_max_upload_mb * 1024 * 1024:
        raise AppError(f"Files are limited to {settings.rag_max_upload_mb} MB.", code="too_large")
    _check_scope(db, curriculum_id, subject_id, chapter_id)
    digest = hashlib.sha256(data).hexdigest()
    dup = db.scalar(
        select(RagDocument).where(
            RagDocument.content_hash == digest,
            RagDocument.curriculum_id == curriculum_id,
            RagDocument.status != DocumentStatus.ARCHIVED,
        )
    )
    if dup is not None:
        raise Conflict(f"This file is already uploaded as “{dup.title}”.", code="duplicate")
    version = 1
    if replaces_id is not None:
        old = get_or_404(db, replaces_id)
        version = old.version + 1
    try:
        ex = extract(file_name, data)
    except ExtractionError as e:
        raise AppError(str(e), code="unreadable_file") from e

    doc = RagDocument(
        title=title.strip() or file_name,
        description=description,
        source_type=source_type,
        licence=licence,
        licence_note=licence_note,
        curriculum_id=curriculum_id,
        subject_id=subject_id,
        chapter_id=chapter_id,
        version=version,
        replaces_id=replaces_id,
        file_name=re.sub(r"[^\w.\- ]", "_", file_name)[:255],
        mime_type=ex.mime_type,
        size_bytes=len(data),
        content_hash=digest,
        text=ex.text,
        page_count=ex.page_count,
        is_sample=is_sample,
        created_by=actor,
    )
    db.add(doc)
    db.flush()
    if settings.r2_configured:
        try:
            doc.storage_key = storage.upload(
                f"rag/{doc.id}/{doc.file_name}", data, content_type=ex.mime_type
            )
        except Exception:  # noqa: BLE001 — the extracted text is enough to keep going
            log.exception("Couldn't store the original file for document %s", doc.id)
    process(db, doc)
    return doc


def process(db: Session, doc: RagDocument) -> None:
    """(Re)build passages from the stored text. Sends the document back to review."""
    cfg = ai_config.get_settings(db)
    db.query(RagChunk).filter(RagChunk.document_id == doc.id).delete()
    concepts = _concepts_for(db, doc.subject_id, doc.chapter_id)
    pieces = chunk(doc.text, target=cfg.chunk_target_tokens, overlap=cfg.chunk_overlap_tokens)
    for i, c in enumerate(pieces):
        ids = map_concepts(c, concepts)
        db.add(
            RagChunk(
                document_id=doc.id,
                ordinal=i,
                heading=c.heading[:300],
                page=c.page,
                text=c.text,
                token_count=c.token_count,
                chapter_id=doc.chapter_id or _chapter_of(db, ids),
                concept_ids=ids,
            )
        )
    doc.chunk_count = len(pieces)
    doc.embedded_count = 0
    doc.embedding_error = None
    doc.error = None if pieces else "No passages could be made from this document."
    doc.status = DocumentStatus.REVIEW if pieces else DocumentStatus.FAILED
    db.flush()


def embed_document(db: Session, doc_id: uuid.UUID, *, user_id: uuid.UUID | None = None) -> int:
    """Embed passages that have no vector from the current model. Returns how many."""
    emb = embeddings.get_embedder()
    doc = db.get(RagDocument, doc_id)
    if emb is None or doc is None:
        return 0
    rows = list(
        db.scalars(
            select(RagChunk)
            .where(
                RagChunk.document_id == doc_id,
                (RagChunk.embedding.is_(None)) | (RagChunk.embedding_model != emb.model_id),
            )
            .order_by(RagChunk.ordinal)
        )
    )
    if rows:
        try:
            res = emb.embed([f"{r.heading}\n{r.text}".strip() for r in rows])
        except LLMError as e:
            doc.embedding_error = str(e)[:300]
            ai_config.record_usage(
                db, feature="embedding", provider=emb.name, model=emb.model, user_id=user_id,
                ok=False, error_code=e.code,
            )  # fmt: skip
            return 0
        for r, v in zip(rows, res.vectors, strict=True):
            r.embedding, r.embedding_model = v, emb.model_id
        ai_config.record_usage(
            db, feature="embedding", provider=emb.name, model=emb.model, user_id=user_id,
            input_tokens=res.input_tokens, latency_ms=res.latency_ms,
        )  # fmt: skip
    doc.embedded_count = (
        db.scalar(
            select(func.count())
            .select_from(RagChunk)
            .where(RagChunk.document_id == doc_id, RagChunk.embedding_model == emb.model_id)
        )
        or 0
    )
    doc.embedding_error = None
    db.flush()
    return len(rows)


def approve(db: Session, doc: RagDocument, actor: uuid.UUID) -> RagDocument:
    if doc.status not in (DocumentStatus.REVIEW, DocumentStatus.ARCHIVED):
        raise Conflict("Only documents waiting for review can be approved.", code="bad_status")
    if doc.licence == Licence.UNKNOWN:
        raise AppError(
            "Record the licence before approving — material with an unknown licence can't be "
            "shown to students.",
            code="licence_required",
        )
    if doc.chunk_count == 0:
        raise AppError("This document has no passages to approve.", code="empty")
    doc.status = DocumentStatus.APPROVED
    doc.approved_by, doc.approved_at = actor, _now()
    if doc.replaces_id:
        old = db.get(RagDocument, doc.replaces_id)
        if old is not None and old.status == DocumentStatus.APPROVED:
            old.status = DocumentStatus.ARCHIVED
    db.flush()
    return doc


def archive(db: Session, doc: RagDocument) -> None:
    doc.status = DocumentStatus.ARCHIVED


def set_chunk_concepts(db: Session, chunk_id: int, concept_ids: list[int]) -> RagChunk:
    c = db.get(RagChunk, chunk_id)
    if c is None:
        raise NotFound("Passage not found.")
    doc = db.get(RagDocument, c.document_id)
    allowed = {x["id"] for x in _concepts_for(db, doc.subject_id, None)}
    bad = [i for i in concept_ids if i not in allowed]
    if bad:
        raise AppError("Choose concepts from this document's subject.", code="bad_concepts")
    c.concept_ids = list(dict.fromkeys(concept_ids))[:6]
    c.concepts_edited = True
    c.chapter_id = doc.chapter_id or _chapter_of(db, c.concept_ids)
    return c


# ── admin views ──────────────────────────────────────────────────────────────


def document_dict(d: RagDocument, names: dict | None = None) -> dict:
    names = names or {}
    return {
        "id": d.id,
        "title": d.title,
        "description": d.description,
        "source_type": d.source_type.value,
        "licence": d.licence.value,
        "licence_note": d.licence_note,
        "curriculum_id": d.curriculum_id,
        "subject": {"id": d.subject_id, "name": names.get(("s", d.subject_id))},
        "chapter": (
            {"id": d.chapter_id, "name": names.get(("c", d.chapter_id))} if d.chapter_id else None
        ),
        "status": d.status.value,
        "version": d.version,
        "replaces_id": d.replaces_id,
        "file_name": d.file_name,
        "mime_type": d.mime_type,
        "size_bytes": d.size_bytes,
        "page_count": d.page_count,
        "chunk_count": d.chunk_count,
        "embedded_count": d.embedded_count,
        "embedding_error": d.embedding_error,
        "error": d.error,
        "is_sample": d.is_sample,
        "approved_at": d.approved_at,
        "created_at": d.created_at,
        "updated_at": d.updated_at,
    }


def _names(db: Session, docs: list[RagDocument]) -> dict:
    sids = {d.subject_id for d in docs}
    cids = {d.chapter_id for d in docs if d.chapter_id}
    out: dict = {}
    if sids:
        out |= {
            ("s", i): n
            for i, n in db.execute(select(Subject.id, Subject.name).where(Subject.id.in_(sids)))
        }  # noqa: E501
    if cids:
        out |= {
            ("c", i): n
            for i, n in db.execute(select(Chapter.id, Chapter.name).where(Chapter.id.in_(cids)))
        }  # noqa: E501
    return out


def list_documents(
    db: Session,
    *,
    status: str | None = None,
    curriculum_id: int | None = None,
    subject_id: int | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    stmt = select(RagDocument)
    if status:
        stmt = stmt.where(RagDocument.status == DocumentStatus(status))
    if curriculum_id:
        stmt = stmt.where(RagDocument.curriculum_id == curriculum_id)
    if subject_id:
        stmt = stmt.where(RagDocument.subject_id == subject_id)
    if q:
        stmt = stmt.where(RagDocument.title.ilike(f"%{q}%"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    docs = list(
        db.scalars(
            stmt.order_by(RagDocument.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    names = _names(db, docs)
    return [document_dict(d, names) for d in docs], total


def detail(db: Session, doc: RagDocument, *, page: int = 1, page_size: int = 50) -> dict:
    chunks = list(
        db.scalars(
            select(RagChunk)
            .where(RagChunk.document_id == doc.id)
            .order_by(RagChunk.ordinal)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    cids = {i for c in chunks for i in c.concept_ids}
    cnames = (
        dict(db.execute(select(Concept.id, Concept.name).where(Concept.id.in_(cids))).all())
        if cids
        else {}
    )
    emb = embeddings.get_embedder()
    return {
        **document_dict(doc, _names(db, [doc])),
        "concepts": _concepts_for(db, doc.subject_id, None),
        "chunks": [
            {
                "id": c.id,
                "ordinal": c.ordinal,
                "heading": c.heading,
                "page": c.page,
                "text": c.text,
                "token_count": c.token_count,
                "concepts": [{"id": i, "name": cnames.get(i, "?")} for i in c.concept_ids],
                "concepts_edited": c.concepts_edited,
                "embedded": c.embedding_model is not None
                and emb is not None
                and c.embedding_model == emb.model_id,
            }
            for c in chunks
        ],
        "chunks_page": page,
    }


def stats(db: Session) -> dict:
    rows = dict(
        db.execute(select(RagDocument.status, func.count()).group_by(RagDocument.status)).all()
    )
    emb = embeddings.get_embedder()
    approved_chunks = (
        select(RagChunk.id).join(RagDocument).where(RagDocument.status == DocumentStatus.APPROVED)
    )
    total_chunks = db.scalar(select(func.count()).select_from(approved_chunks.subquery())) or 0
    embedded = (
        db.scalar(
            select(func.count()).select_from(
                approved_chunks.where(RagChunk.embedding_model == emb.model_id).subquery()
            )
        )
        if emb
        else 0
    )
    return {
        "documents": {s.value: rows.get(s, 0) for s in DocumentStatus},
        "approved_passages": total_chunks,
        "embedded_passages": embedded or 0,
    }


# ── retrieval ────────────────────────────────────────────────────────────────


@dataclass
class Hit:
    chunk_id: int
    document_id: uuid.UUID
    title: str
    source_type: str
    heading: str
    page: int | None
    text: str
    concept_ids: list[int]
    score: float = 0.0
    keyword_rank: int | None = None
    similarity: float | None = None
    concept_match: bool = False
    signals: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "title": self.title,
            "source_type": self.source_type,
            "heading": self.heading,
            "page": self.page,
            "text": self.text,
            "score": round(self.score, 5),
            "keyword_rank": self.keyword_rank,
            "similarity": None if self.similarity is None else round(self.similarity, 4),
            "concept_match": self.concept_match,
        }


@dataclass
class Retrieval:
    hits: list[Hit]
    mode: str  # hybrid | keyword
    embedding_error: str | None = None


_OR_QUERY = text("replace(plainto_tsquery('english', :q)::text, ' & ', ' | ')")


def _keyword(db: Session, base, query: str, limit: int = 20) -> list:
    tsq = db.scalar(select(_OR_QUERY), {"q": query}) if query else ""
    lexemes = list(dict.fromkeys(re.findall(r"'((?:[^']|'')+)'", tsq or "")))[:16]
    if not lexemes:
        return []
    terms = [func.to_tsquery("simple", f"'{lx}'") for lx in lexemes]
    scope = base.subquery()
    n_total = db.scalar(select(func.count()).select_from(scope)) or 0
    df_row = db.execute(
        select(*[func.count().filter(scope.c.search.op("@@")(t)) for t in terms]).select_from(scope)
    ).one()
    idf = [math.log(1 + n_total / max(df, 1)) for df in df_row]
    q = func.to_tsquery("simple", tsq)  # lexemes are already stemmed — don't stem twice
    rows = db.execute(
        base.add_columns(
            func.ts_rank_cd(RagChunk.search, q).label("r"),
            *[RagChunk.search.op("@@")(t).label(f"m{i}") for i, t in enumerate(terms)],
        )
        .where(RagChunk.search.op("@@")(q))
        .limit(300)
    ).all()
    scored = []
    for row in rows:
        c, title, stype, density, *matches = row
        weight = sum(w for w, m in zip(idf, matches, strict=True) if m)
        scored.append((weight, density, -c.id, (c, title, stype)))
    scored.sort(key=lambda x: x[:3], reverse=True)
    return [r for *_, r in scored[:limit]]


def retrieve(
    db: Session,
    query: str,
    *,
    curriculum_id: int,
    subject_ids: list[int] | None = None,
    chapter_id: int | None = None,
    concept_ids: list[int] | None = None,
    k: int = 4,
    min_similarity: float = 0.3,
    include_unapproved: bool = False,
    user_id: uuid.UUID | None = None,
) -> Retrieval:
    query = (query or "").strip()[:1000]
    statuses = [DocumentStatus.APPROVED]
    if include_unapproved:  # admin playground only
        statuses.append(DocumentStatus.REVIEW)
    base = (
        select(RagChunk, RagDocument.title, RagDocument.source_type)
        .join(RagDocument, RagDocument.id == RagChunk.document_id)
        .where(RagDocument.status.in_(statuses), RagDocument.curriculum_id == curriculum_id)
    )
    if subject_ids is not None:
        base = base.where(RagDocument.subject_id.in_(subject_ids or [-1]))

    found: dict[int, Hit] = {}

    def hit(row) -> Hit:
        c, title, stype = row
        return found.setdefault(
            c.id,
            Hit(c.id, c.document_id, title, stype.value, c.heading, c.page, c.text, c.concept_ids),
        )

    # 1. keyword: any of the query's words, each weighted by how rare it is in scope (IDF),
    #    so "centripetal" counts for more than "force"; cover density breaks ties.
    for rank, row in enumerate(_keyword(db, base, query), start=1):
        h = hit(row)
        h.keyword_rank = rank
        h.score += 1 / (RRF_K + rank)

    # 2. semantic (when an embedding model is set up)
    mode, emb_error = "keyword", None
    emb = embeddings.get_embedder()
    if emb is not None and query:
        try:
            res = emb.embed([query], kind="query")
            ai_config.record_usage(
                db, feature="embedding", provider=emb.name, model=emb.model, user_id=user_id,
                input_tokens=res.input_tokens, latency_ms=res.latency_ms,
            )  # fmt: skip
            qv = res.vectors[0]
            dist = RagChunk.embedding.cosine_distance(qv)
            rows = db.execute(
                base.add_columns(dist.label("d"))
                .where(RagChunk.embedding_model == emb.model_id)
                .order_by(dist)
                .limit(20)
            ).all()
            mode = "hybrid"
            rank = 0
            for c, title, stype, d in rows:
                sim = 1 - float(d)
                if sim < min_similarity:
                    continue
                rank += 1
                h = hit((c, title, stype))
                h.similarity = sim
                h.score += 1 / (RRF_K + rank)
        except LLMError as e:  # fall back to keyword-only, but say so
            emb_error = e.code
            ai_config.record_usage(
                db, feature="embedding", provider=emb.name, model=emb.model, user_id=user_id,
                ok=False, error_code=e.code,
            )  # fmt: skip

    # 3. light rerank: passages about the concepts (or chapter) in question rank higher
    wanted = set(concept_ids or [])
    chapters = (
        dict(
            db.execute(select(RagChunk.id, RagChunk.chapter_id).where(RagChunk.id.in_(found))).all()
        )
        if chapter_id is not None and found
        else {}
    )
    for h in found.values():
        if wanted and wanted & set(h.concept_ids):
            h.concept_match = True
            h.score += 0.5 / (RRF_K + 1)
        elif chapters.get(h.chunk_id) == chapter_id:
            h.score += 0.2 / (RRF_K + 1)

    # 4. too few matches → fill with passages tagged to the concept itself
    if wanted and len(found) < k:
        rows = db.execute(
            base.where(RagChunk.concept_ids.overlap(list(wanted)))
            .order_by(RagChunk.document_id, RagChunk.ordinal)
            .limit(k * 2)
        ).all()
        for row in rows:
            if row[0].id not in found:
                h = hit(row)
                h.concept_match = True
                h.score += 0.25 / (RRF_K + 1)
            if len(found) >= k:
                break

    hits = sorted(found.values(), key=lambda h: (-h.score, h.chunk_id))[:k]
    return Retrieval(hits, mode, emb_error)


# ── retrieval evaluation ────────────────────────────────────────────────────


def eval_case_dict(c: RagEvalCase, titles: dict) -> dict:
    return {
        "id": c.id,
        "query": c.query,
        "curriculum_id": c.curriculum_id,
        "subject_id": c.subject_id,
        "expected_document_id": c.expected_document_id,
        "expected_document_title": titles.get(c.expected_document_id),
        "expected_phrase": c.expected_phrase,
        "created_at": c.created_at,
    }


def list_eval_cases(db: Session) -> list[dict]:
    cases = list(db.scalars(select(RagEvalCase).order_by(RagEvalCase.created_at)))
    ids = {c.expected_document_id for c in cases}
    titles = (
        dict(
            db.execute(
                select(RagDocument.id, RagDocument.title).where(RagDocument.id.in_(ids))
            ).all()
        )
        if ids
        else {}
    )
    return [eval_case_dict(c, titles) for c in cases]


def run_eval(db: Session, actor: uuid.UUID, *, k: int = 4) -> RagEvalRun:
    cfg = ai_config.get_settings(db)
    cases = list(db.scalars(select(RagEvalCase).order_by(RagEvalCase.created_at)))
    if not cases:
        raise AppError("Add at least one test query first.", code="no_cases")
    results, hits, rr_total, mode = [], 0, 0.0, "keyword"
    for case in cases:
        r = retrieve(
            db,
            case.query,
            curriculum_id=case.curriculum_id,
            subject_ids=[case.subject_id] if case.subject_id else None,
            k=k,
            min_similarity=cfg.min_similarity,
        )
        mode = r.mode
        phrase = case.expected_phrase.lower().strip()
        rank = next(
            (
                i
                for i, h in enumerate(r.hits, start=1)
                if h.document_id == case.expected_document_id
                and (not phrase or phrase in h.text.lower())
            ),
            None,
        )
        hits += rank is not None
        rr_total += 1 / rank if rank else 0.0
        results.append(
            {
                "case_id": str(case.id),
                "query": case.query,
                "rank": rank,
                "top": [
                    {"title": h.title, "heading": h.heading, "score": round(h.score, 5)}
                    for h in r.hits
                ],
            }
        )
    run = RagEvalRun(
        k=k,
        retrieval=mode,
        cases=len(cases),
        hit_rate=hits / len(cases),
        mrr=rr_total / len(cases),
        results=results,
        run_by=actor,
    )
    db.add(run)
    db.flush()
    return run


def eval_run_dict(r: RagEvalRun) -> dict:
    return {
        "id": r.id,
        "k": r.k,
        "retrieval": r.retrieval,
        "cases": r.cases,
        "hit_rate": r.hit_rate,
        "mrr": r.mrr,
        "results": r.results,
        "created_at": r.created_at,
    }
