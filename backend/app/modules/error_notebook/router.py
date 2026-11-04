"""/api/v1/error-notebook — mistakes and saved questions, with explanations."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.config.database import DbSession, transaction
from app.modules.curriculum import service as curriculum
from app.modules.error_notebook import service
from app.modules.error_notebook.models import EntryStatus, ErrorNotebookEntry, MistakeCategory
from app.modules.practice.models import QuestionAttempt
from app.modules.practice.service import recent_attempts_exist
from app.modules.question_bank import evaluation as ev
from app.modules.question_bank import service as qbank
from app.modules.question_bank.models import Question, QuestionVersion
from app.shared.permissions import CurrentStudent

router = APIRouter(prefix="/error-notebook", tags=["error-notebook"])


class SaveQuestion(BaseModel):
    question_id: uuid.UUID
    note: str | None = Field(default=None, max_length=1000)


class UpdateEntry(BaseModel):
    category: MistakeCategory | None = None
    note: str | None = Field(default=None, max_length=1000)
    status: EntryStatus | None = None


def _entry(db, e: ErrorNotebookEntry) -> dict:
    q = db.get(Question, e.question_id)
    attempt = db.get(QuestionAttempt, e.last_attempt_id) if e.last_attempt_id else None
    # Show the version the student last answered (history), else the live one.
    vid = attempt.question_version_id if attempt else q.published_version_id
    v = db.get(QuestionVersion, vid)
    ctx = curriculum.concept_context(db, [c.concept_id for c in q.concepts])
    reveal = (
        ev.evaluate(v.type, v.content, v.answer, attempt.response).correct_answer if attempt else {}
    )
    return {
        "id": e.id,
        "question_id": q.id,
        "source": e.source,
        "category": e.category.value,
        "note": e.note,
        "status": e.status.value,
        "times_wrong": e.times_wrong,
        "times_right_since": e.times_right_since,
        "created_at": e.created_at,
        "updated_at": e.updated_at,
        "resolved_at": e.resolved_at,
        "question": {**qbank.student_view(v), "concepts": list(ctx.values())},
        "your_answer": attempt.response if attempt else None,
        "last_evaluation": attempt.evaluation.value if attempt else None,
        "correct_answer": reveal,
        "solution": v.solution,
        "can_reattempt": bool(q.published_version_id and not q.archived_at),
    }


@router.get("")
def list_entries(
    p: CurrentStudent,
    db: DbSession,
    status_: Annotated[EntryStatus | None, Query(alias="status")] = None,
    category: MistakeCategory | None = None,
):
    stmt = select(ErrorNotebookEntry).where(ErrorNotebookEntry.student_id == p.user_id)
    if status_:
        stmt = stmt.where(ErrorNotebookEntry.status == status_)
    if category:
        stmt = stmt.where(ErrorNotebookEntry.category == category)
    entries = db.scalars(stmt.order_by(ErrorNotebookEntry.updated_at.desc()).limit(200))
    return [_entry(db, e) for e in entries]


@router.post("", status_code=status.HTTP_201_CREATED)
def save(body: SaveQuestion, p: CurrentStudent, db: DbSession):
    with transaction(db):
        e = service.save_question(
            db,
            p.user_id,
            body.question_id,
            body.note,
            recent_attempts_exist(db, p.user_id, body.question_id),
        )
        db.flush()
        last = db.scalar(
            select(QuestionAttempt.id)
            .where(
                QuestionAttempt.student_id == p.user_id,
                QuestionAttempt.question_id == body.question_id,
            )
            .order_by(QuestionAttempt.created_at.desc())
            .limit(1)
        )
        e.last_attempt_id = e.last_attempt_id or last
    return _entry(db, e)


@router.patch("/{entry_id}")
def update(entry_id: uuid.UUID, body: UpdateEntry, p: CurrentStudent, db: DbSession):
    with transaction(db):
        e = service.update(
            db,
            service.get_owned(db, p.user_id, entry_id),
            category=body.category,
            note=body.note,
            status=body.status,
        )
    return _entry(db, e)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove(entry_id: uuid.UUID, p: CurrentStudent, db: DbSession):
    with transaction(db):
        db.delete(service.get_owned(db, p.user_id, entry_id))
