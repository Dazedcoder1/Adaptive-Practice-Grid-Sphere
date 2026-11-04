"""/api/v1/practice — sessions, question delivery, answers, hints, reports."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Header, Query, status

from app.config.database import DbSession, transaction
from app.config.settings import settings
from app.modules.practice import service
from app.modules.practice.schemas import CreateSession, SubmitAnswer
from app.shared.consumers import process_inline
from app.shared.exceptions import AppError
from app.shared.permissions import CurrentStudent

router = APIRouter(prefix="/practice", tags=["practice"])


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
def create(body: CreateSession, p: CurrentStudent, db: DbSession):
    with transaction(db):
        s = service.create_session(db, p.user_id, **body.model_dump())
    return service.session_summary(s)


@router.get("/sessions")
def sessions(
    p: CurrentStudent,
    db: DbSession,
    status_: Annotated[
        str | None, Query(alias="status", pattern="^(open|active|paused|completed)$")
    ] = None,  # noqa: E501
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
):
    return service.list_sessions(db, p.user_id, status=status_, limit=limit)


@router.get("/sessions/{session_id}")
def get_session(session_id: uuid.UUID, p: CurrentStudent, db: DbSession):
    return service.session_summary(service.get_owned(db, p.user_id, session_id))


@router.post("/sessions/{session_id}/next")
def next_question(session_id: uuid.UUID, p: CurrentStudent, db: DbSession):
    """The current unanswered question, or a newly selected one. Safe to call repeatedly."""
    with transaction(db):
        return service.next_question(db, p.user_id, session_id)


@router.post("/sessions/{session_id}/questions/{sq_id}/hint")
def hint(session_id: uuid.UUID, sq_id: uuid.UUID, p: CurrentStudent, db: DbSession):
    with transaction(db):
        return service.reveal_hint(db, p.user_id, session_id, sq_id)


@router.post("/attempts")
def submit(
    body: SubmitAnswer,
    p: CurrentStudent,
    db: DbSession,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key", max_length=80)] = None,
):
    if not idempotency_key or len(idempotency_key) < 8:
        raise AppError(
            "Send an Idempotency-Key header with each answer.", code="idempotency_key_required"
        )
    with transaction(db):
        attempt, events, _ = service.submit_answer(
            db, p.user_id, body.session_question_id, body.response, idempotency_key
        )
    if events and settings.process_events_inline:
        process_inline(events)
    return service.feedback(db, attempt)


@router.post("/sessions/{session_id}/{action}")
def lifecycle(session_id: uuid.UUID, action: Annotated[str, ...], p: CurrentStudent, db: DbSession):
    if action not in ("pause", "resume", "complete"):
        raise AppError("Unknown action.", code="bad_action")
    with transaction(db):
        s = service.set_status(db, p.user_id, session_id, action)
    return service.session_summary(s)


@router.get("/sessions/{session_id}/report")
def report(session_id: uuid.UUID, p: CurrentStudent, db: DbSession):
    return service.report(db, p.user_id, session_id)
