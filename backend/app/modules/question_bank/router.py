"""/api/v1/admin/questions — author, version, review, publish and import questions."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.config.database import DbSession, transaction
from app.modules.administration.schemas import Page
from app.modules.audit import service as audit
from app.modules.question_bank import service
from app.modules.question_bank.models import QuestionType
from app.modules.question_bank.schemas import (
    ImportQuestions,
    ImportResult,
    QuestionIn,
    RejectNote,
    ReviewNote,
)
from app.shared.exceptions import AppError
from app.shared.permissions import Principal, require_permission
from app.shared.request import client_ip

router = APIRouter(prefix="/admin/questions", tags=["admin: question bank"])
Editor = Annotated[Principal, Depends(require_permission("questions.manage"))]
Approver = Annotated[Principal, Depends(require_permission("questions.approve"))]


def _input(body: QuestionIn) -> service.QuestionInput:
    return service.QuestionInput(
        type=body.type,
        difficulty=body.difficulty,
        stem=body.stem,
        content=body.content,
        answer=body.answer,
        solution=body.solution,
        hints=body.hints,
        estimated_seconds=body.estimated_seconds,
        source=body.source,
        concepts=[(c.concept_id, c.weight) for c in body.concepts],
    )


def _log(db, p, request, action, qid, details=None):
    audit.record(
        db,
        action,
        actor_user_id=p.user_id,
        target_type="question",
        target_id=qid,
        details=details or {},
        ip=client_ip(request),
    )


@router.get("", response_model=Page[dict])
def list_questions(
    _: Editor,
    db: DbSession,
    status_: Annotated[
        str | None, Query(alias="status", pattern="^(draft|in_review|rejected|published|archived)$")
    ] = None,  # noqa: E501
    concept_id: int | None = None,
    type: QuestionType | None = None,
    difficulty: Annotated[int | None, Query(ge=1, le=5)] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    items, total = service.list_questions(
        db,
        status=status_,
        concept_id=concept_id,
        qtype=type,
        q=q,
        difficulty=difficulty,
        page=page,
        page_size=page_size,
    )
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/stats")
def stats(_: Editor, db: DbSession):
    return service.bank_stats(db)


@router.get("/{question_id}")
def get_question(question_id: uuid.UUID, _: Editor, db: DbSession):
    return service.detail(db, service.get_or_404(db, question_id))


@router.post("", status_code=status.HTTP_201_CREATED)
def create(body: QuestionIn, request: Request, p: Editor, db: DbSession):
    with transaction(db):
        q = service.create(db, _input(body), p.user_id)
        _log(db, p, request, "question.created", q.id)
    return service.detail(db, q)


@router.put("/{question_id}")
def save(question_id: uuid.UUID, body: QuestionIn, request: Request, p: Editor, db: DbSession):
    with transaction(db):
        q = service.get_or_404(db, question_id)
        v = service.save_draft(db, q, _input(body), p.user_id)
        _log(db, p, request, "question.edited", q.id, {"version": v.version})
    return service.detail(db, q)


@router.post("/{question_id}/submit")
def submit(question_id: uuid.UUID, request: Request, p: Editor, db: DbSession):
    with transaction(db):
        q = service.get_or_404(db, question_id)
        v = service.submit(db, q, p.user_id)
        _log(db, p, request, "question.submitted", q.id, {"version": v.version})
    return service.detail(db, q)


@router.post("/{question_id}/publish")
def publish(question_id: uuid.UUID, body: ReviewNote, request: Request, p: Approver, db: DbSession):
    with transaction(db):
        q = service.get_or_404(db, question_id)
        v = service.publish(db, q, p.user_id, note=body.note)
        _log(db, p, request, "question.published", q.id, {"version": v.version})
    return service.detail(db, q)


@router.post("/{question_id}/reject")
def reject(question_id: uuid.UUID, body: RejectNote, request: Request, p: Approver, db: DbSession):
    with transaction(db):
        q = service.get_or_404(db, question_id)
        v = service.reject(db, q, p.user_id, body.note)
        _log(db, p, request, "question.rejected", q.id, {"version": v.version, "note": body.note})
    return service.detail(db, q)


@router.post("/{question_id}/archive")
def archive(question_id: uuid.UUID, request: Request, p: Editor, db: DbSession):
    with transaction(db):
        q = service.get_or_404(db, question_id)
        service.archive(db, q)
        _log(db, p, request, "question.archived", q.id)
    return service.detail(db, q)


@router.post("/{question_id}/restore")
def restore(question_id: uuid.UUID, request: Request, p: Editor, db: DbSession):
    with transaction(db):
        q = service.get_or_404(db, question_id)
        service.restore(db, q)
        _log(db, p, request, "question.restored", q.id)
    return service.detail(db, q)


@router.post("/import", status_code=status.HTTP_201_CREATED, response_model=ImportResult)
def bulk_import(body: ImportQuestions, request: Request, p: Editor, db: DbSession):
    """All-or-nothing: any invalid question rejects the whole file, with its position."""
    if body.publish and "questions.approve" not in p.permissions:
        raise AppError("Publishing on import needs approval permission.", code="forbidden")
    with transaction(db):
        ids = []
        for i, item in enumerate(body.questions, start=1):
            try:
                q = service.create(db, _input(item), p.user_id)
            except AppError as e:
                raise AppError(f"Question {i}: {e.message}", code=e.code) from e
            if body.publish:
                service.publish(db, q, p.user_id, note="bulk import")
            ids.append(q.id)
        audit.record(
            db,
            "question.bulk_imported",
            actor_user_id=p.user_id,
            target_type="question",
            details={"count": len(ids), "published": body.publish},
            ip=client_ip(request),
        )
    return ImportResult(created=ids, published=body.publish)
