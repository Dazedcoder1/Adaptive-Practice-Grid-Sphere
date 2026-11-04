"""Error notebook: wrong answers are added automatically; students can save questions too."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.error_notebook.models import EntryStatus, ErrorNotebookEntry, MistakeCategory
from app.shared.exceptions import AppError, NotFound


def on_question_answered(db: Session, event_id: uuid.UUID, payload: dict) -> None:
    evaluation = payload["evaluation"]
    if evaluation == "ungraded":
        return
    student_id = uuid.UUID(payload["student_id"])
    question_id = uuid.UUID(payload["question_id"])
    attempt_id = uuid.UUID(payload["attempt_id"])
    entry = db.scalar(
        select(ErrorNotebookEntry)
        .where(
            ErrorNotebookEntry.student_id == student_id,
            ErrorNotebookEntry.question_id == question_id,
        )
        .with_for_update()
    )
    if evaluation in ("incorrect", "partial"):
        if entry is None:
            entry = ErrorNotebookEntry(
                student_id=student_id,
                question_id=question_id,
                source="mistake",
                times_wrong=0,
                times_right_since=0,
            )
            db.add(entry)
        entry.times_wrong += 1
        entry.times_right_since = 0
        entry.status = EntryStatus.OPEN
        entry.resolved_at = None
        entry.last_attempt_id = attempt_id
    elif entry is not None:
        entry.times_right_since += 1
        entry.last_attempt_id = attempt_id


def get_owned(db: Session, student_id: uuid.UUID, entry_id: uuid.UUID) -> ErrorNotebookEntry:
    e = db.get(ErrorNotebookEntry, entry_id)
    if e is None or e.student_id != student_id:
        raise NotFound("Notebook entry not found.")
    return e


def save_question(
    db: Session,
    student_id: uuid.UUID,
    question_id: uuid.UUID,
    note: str | None,
    has_attempted: bool,
) -> ErrorNotebookEntry:
    if not has_attempted:
        raise AppError("You can only save questions you've attempted.", code="not_attempted")
    e = db.scalar(
        select(ErrorNotebookEntry).where(
            ErrorNotebookEntry.student_id == student_id,
            ErrorNotebookEntry.question_id == question_id,
        )
    )
    if e is None:
        e = ErrorNotebookEntry(
            student_id=student_id,
            question_id=question_id,
            source="saved",
            times_wrong=0,
            times_right_since=0,
        )
        db.add(e)
    if note is not None:
        e.note = note
    e.status = EntryStatus.OPEN
    return e


def update(
    db: Session,
    e: ErrorNotebookEntry,
    *,
    category: MistakeCategory | None,
    note: str | None,
    status: EntryStatus | None,
) -> ErrorNotebookEntry:
    if category is not None:
        e.category = category
    if note is not None:
        e.note = note.strip() or None
    if status is not None and status != e.status:
        e.status = status
        e.resolved_at = datetime.now(UTC) if status == EntryStatus.RESOLVED else None
    return e


def mistake_summary(db: Session, student_id: uuid.UUID, concept_id: int) -> dict[str, int]:
    """Mistake categories the student has recorded on this concept's questions — evidence
    the AI tutor may use. Only categories the student chose; uncategorised are counted too."""
    from sqlalchemy import func

    from app.modules.question_bank.models import QuestionConcept

    rows = db.execute(
        select(ErrorNotebookEntry.category, func.count())
        .join(QuestionConcept, QuestionConcept.question_id == ErrorNotebookEntry.question_id)
        .where(
            ErrorNotebookEntry.student_id == student_id,
            ErrorNotebookEntry.source == "mistake",
            ErrorNotebookEntry.status == EntryStatus.OPEN,
            QuestionConcept.concept_id == concept_id,
        )
        .group_by(ErrorNotebookEntry.category)
    ).all()
    return {c.value: n for c, n in rows}
