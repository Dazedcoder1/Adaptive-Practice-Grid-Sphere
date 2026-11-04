"""/api/v1/admin/rag — study documents, passages, a retrieval playground and evaluation."""

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, Request, UploadFile
from pydantic import BaseModel, Field

from app.config.database import DbSession, SessionLocal, transaction
from app.config.settings import settings
from app.modules.administration.schemas import Page
from app.modules.ai_tutor import config as ai_config
from app.modules.audit import service as audit
from app.modules.rag import service
from app.modules.rag.models import DocumentStatus, Licence, RagEvalCase, RagEvalRun, SourceType
from app.shared.exceptions import AppError, NotFound
from app.shared.permissions import Principal, require_permission
from app.shared.request import client_ip

log = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/rag", tags=["admin: rag"])
Manager = Annotated[Principal, Depends(require_permission("ai.manage"))]


def embed_in_background(doc_id: uuid.UUID, user_id: uuid.UUID | None) -> None:
    try:
        with SessionLocal() as db, transaction(db):
            service.embed_document(db, doc_id, user_id=user_id)
    except Exception:  # noqa: BLE001 — never crash the request that scheduled it
        log.exception("Embedding failed for document %s", doc_id)


def schedule_embedding(bg: BackgroundTasks, doc_id: uuid.UUID, user_id: uuid.UUID | None):
    if settings.process_events_inline:
        bg.add_task(embed_in_background, doc_id, user_id)
    else:
        from app.workers.celery_app import celery_app

        celery_app.send_task("ai.embed_document", args=[str(doc_id)])


def _log(db, p, request, action, doc_id, details=None):
    audit.record(
        db,
        action,
        actor_user_id=p.user_id,
        target_type="rag_document",
        target_id=doc_id,
        details=details or {},
        ip=client_ip(request),
    )


# ── documents ────────────────────────────────────────────────────────────────


@router.get("/documents", response_model=Page[dict])
def list_documents(
    _: Manager,
    db: DbSession,
    status: Annotated[
        str | None, Query(pattern="^(processing|review|approved|failed|archived)$")
    ] = None,  # noqa: E501
    curriculum_id: int | None = None,
    subject_id: int | None = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    items, total = service.list_documents(
        db,
        status=status,
        curriculum_id=curriculum_id,
        subject_id=subject_id,
        q=q,
        page=page,
        page_size=page_size,
    )
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.post("/documents", status_code=201)
def upload(
    p: Manager,
    db: DbSession,
    request: Request,
    bg: BackgroundTasks,
    file: Annotated[UploadFile, File()],
    title: Annotated[str, Form(max_length=200)],
    curriculum_id: Annotated[int, Form()],
    subject_id: Annotated[int, Form()],
    source_type: Annotated[SourceType, Form()],
    licence: Annotated[Licence, Form()],
    chapter_id: Annotated[int | None, Form()] = None,
    licence_note: Annotated[str, Form(max_length=500)] = "",
    description: Annotated[str, Form(max_length=1000)] = "",
    replaces_id: Annotated[uuid.UUID | None, Form()] = None,
):
    limit = settings.rag_max_upload_mb * 1024 * 1024
    data = file.file.read(limit + 1)  # sync endpoint: runs in the threadpool, not the event loop
    if len(data) > limit:
        raise AppError(f"Files are limited to {settings.rag_max_upload_mb} MB.", code="too_large")
    with transaction(db):
        doc = service.create_document(
            db,
            actor=p.user_id,
            file_name=file.filename or "upload",
            data=data,
            title=title,
            curriculum_id=curriculum_id,
            subject_id=subject_id,
            chapter_id=chapter_id,
            source_type=source_type,
            licence=licence,
            licence_note=licence_note,
            description=description,
            replaces_id=replaces_id,
        )
        _log(db, p, request, "rag.document_uploaded", doc.id, {"title": doc.title})
        out = service.detail(db, doc)
    schedule_embedding(bg, doc.id, p.user_id)
    return out


@router.get("/documents/{doc_id}")
def get_document(
    doc_id: uuid.UUID, _: Manager, db: DbSession, page: Annotated[int, Query(ge=1)] = 1
):
    return service.detail(db, service.get_or_404(db, doc_id), page=page)


class DocumentPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    source_type: SourceType | None = None
    licence: Licence | None = None
    licence_note: str | None = Field(default=None, max_length=500)


@router.patch("/documents/{doc_id}")
def update_document(
    doc_id: uuid.UUID, body: DocumentPatch, p: Manager, db: DbSession, request: Request
):
    with transaction(db):
        doc = service.get_or_404(db, doc_id)
        changes = body.model_dump(exclude_unset=True)
        if doc.status == DocumentStatus.APPROVED and changes.get("licence") == Licence.UNKNOWN:
            raise AppError(
                "Archive the document before marking its licence unknown.", code="bad_licence"
            )  # noqa: E501
        for k, v in changes.items():
            setattr(doc, k, v)
        _log(db, p, request, "rag.document_updated", doc.id, {"fields": sorted(changes)})
        return service.detail(db, doc)


@router.post("/documents/{doc_id}/{action}")
def document_action(
    doc_id: uuid.UUID,
    action: str,
    p: Manager,
    db: DbSession,
    request: Request,
    bg: BackgroundTasks,
):
    if action not in ("approve", "archive", "reprocess", "embed"):
        raise AppError("Unknown action.", code="bad_action")
    with transaction(db):
        doc = service.get_or_404(db, doc_id)
        if action == "approve":
            service.approve(db, doc, p.user_id)
        elif action == "archive":
            service.archive(db, doc)
        elif action == "reprocess":
            service.process(db, doc)
        _log(db, p, request, f"rag.document_{action}", doc.id)
        out = service.detail(db, doc)
    if action in ("reprocess", "embed"):
        schedule_embedding(bg, doc_id, p.user_id)
    return out


class ChunkPatch(BaseModel):
    concept_ids: list[int] = Field(max_length=6)


@router.patch("/chunks/{chunk_id}")
def update_chunk(chunk_id: int, body: ChunkPatch, p: Manager, db: DbSession, request: Request):
    with transaction(db):
        c = service.set_chunk_concepts(db, chunk_id, body.concept_ids)
        _log(db, p, request, "rag.passage_concepts_set", c.document_id, {"chunk_id": chunk_id})
        return {"id": c.id, "concept_ids": c.concept_ids}


# ── retrieval playground & evaluation ────────────────────────────────────────


class SearchIn(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    curriculum_id: int
    subject_id: int | None = None
    concept_id: int | None = None
    k: int = Field(default=5, ge=1, le=20)
    include_unapproved: bool = False


@router.post("/search")
def search(body: SearchIn, p: Manager, db: DbSession):
    """What the tutor would retrieve for a query, with the scores behind the ranking."""
    with transaction(db):
        cfg = ai_config.get_settings(db)
        r = service.retrieve(
            db,
            body.query,
            curriculum_id=body.curriculum_id,
            subject_ids=[body.subject_id] if body.subject_id else None,
            concept_ids=[body.concept_id] if body.concept_id else None,
            k=body.k,
            min_similarity=cfg.min_similarity,
            include_unapproved=body.include_unapproved,
            user_id=p.user_id,
        )
        return {
            "mode": r.mode,
            "embedding_error": r.embedding_error,
            "hits": [h.as_dict() for h in r.hits],
        }


class EvalCaseIn(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    curriculum_id: int
    subject_id: int | None = None
    expected_document_id: uuid.UUID
    expected_phrase: str = Field(default="", max_length=200)


@router.get("/eval-cases")
def eval_cases(_: Manager, db: DbSession):
    return service.list_eval_cases(db)


@router.post("/eval-cases", status_code=201)
def add_eval_case(body: EvalCaseIn, p: Manager, db: DbSession):
    with transaction(db):
        service.get_or_404(db, body.expected_document_id)
        db.add(RagEvalCase(**body.model_dump(), created_by=p.user_id))
    return service.list_eval_cases(db)


@router.delete("/eval-cases/{case_id}", status_code=204)
def delete_eval_case(case_id: uuid.UUID, _: Manager, db: DbSession):
    with transaction(db):
        c = db.get(RagEvalCase, case_id)
        if c is None:
            raise NotFound("Test query not found.")
        db.delete(c)


@router.post("/eval-runs")
def run_eval(p: Manager, db: DbSession, k: Annotated[int, Query(ge=1, le=10)] = 4):
    with transaction(db):
        return service.eval_run_dict(service.run_eval(db, p.user_id, k=k))


@router.get("/eval-runs")
def eval_runs(_: Manager, db: DbSession):
    from sqlalchemy import select

    runs = db.scalars(select(RagEvalRun).order_by(RagEvalRun.created_at.desc()).limit(10))
    return [service.eval_run_dict(r) for r in runs]
