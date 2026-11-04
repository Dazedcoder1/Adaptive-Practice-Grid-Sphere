"""Question bank: authoring, versioning, review/publication, and the student-safe view."""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.curriculum.models import Concept
from app.modules.question_bank import evaluation
from app.modules.question_bank.models import (
    Question,
    QuestionConcept,
    QuestionType,
    QuestionVersion,
    VersionStatus,
)
from app.shared.exceptions import AppError, Conflict, NotFound


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass
class QuestionInput:
    type: QuestionType
    difficulty: int
    stem: str
    content: dict[str, Any] = field(default_factory=dict)
    answer: dict[str, Any] = field(default_factory=dict)
    solution: str = ""
    hints: list[str] = field(default_factory=list)
    estimated_seconds: int = 90
    source: str | None = None
    concepts: list[tuple[int, float]] = field(default_factory=list)  # (concept_id, weight)


def _check(data: QuestionInput) -> None:
    if not data.stem.strip():
        raise AppError("The question needs text.", code="invalid_question")
    if not 1 <= data.difficulty <= 5:
        raise AppError("Difficulty must be 1–5.", code="invalid_question")
    if not data.concepts:
        raise AppError("Map the question to at least one concept.", code="invalid_question")
    if any(not 0 < w <= 1 for _, w in data.concepts):
        raise AppError("Concept weights must be between 0 and 1.", code="invalid_question")
    if data.type == QuestionType.FILL_BLANK and data.stem.count("___") != data.content.get(
        "blanks"
    ):
        raise AppError("Mark each blank in the question with ___ .", code="invalid_question")
    try:
        evaluation.validate(data.type, data.content, data.answer)
    except evaluation.InvalidQuestion as e:
        raise AppError(str(e), code="invalid_question") from e


def _set_concepts(db: Session, q: Question, concepts: list[tuple[int, float]]) -> None:
    ids = [c for c, _ in concepts]
    found = set(db.scalars(select(Concept.id).where(Concept.id.in_(ids))))
    if missing := set(ids) - found:
        raise NotFound(f"Unknown concept(s): {sorted(missing)}")
    q.concepts = [QuestionConcept(concept_id=c, weight=w) for c, w in dict(concepts).items()]


def _apply(v: QuestionVersion, data: QuestionInput) -> None:
    v.type, v.difficulty, v.stem = data.type, data.difficulty, data.stem.strip()
    v.content, v.answer = data.content, data.answer
    v.solution, v.hints = data.solution.strip(), [h.strip() for h in data.hints if h.strip()]
    v.estimated_seconds, v.source = data.estimated_seconds, data.source


def create(
    db: Session, data: QuestionInput, actor: uuid.UUID | None, *, is_sample: bool = False
) -> Question:
    _check(data)
    q = Question(created_by=actor, is_sample=is_sample)
    db.add(q)
    db.flush()
    _set_concepts(db, q, data.concepts)
    v = QuestionVersion(question_id=q.id, version=1, status=VersionStatus.DRAFT, created_by=actor)
    _apply(v, data)
    db.add(v)
    db.flush()
    q.latest_version_id = v.id
    return q


def save_draft(db: Session, q: Question, data: QuestionInput, actor: uuid.UUID) -> QuestionVersion:
    """Edit the draft in place; if the latest version is locked, start a new version."""
    _check(data)
    if q.archived_at:
        raise Conflict("Restore the question before editing it.", code="archived")
    latest = db.get(QuestionVersion, q.latest_version_id)
    # Never-served versions change in place (an in-review edit goes back to draft).
    # Anything students may have seen is immutable, so editing it starts a new version.
    if latest.status in (VersionStatus.DRAFT, VersionStatus.REJECTED, VersionStatus.IN_REVIEW):
        target = latest
        target.status, target.submitted_at = VersionStatus.DRAFT, None
    else:
        target = QuestionVersion(
            question_id=q.id,
            version=latest.version + 1,
            status=VersionStatus.DRAFT,
            created_by=actor,
        )
        db.add(target)
    _apply(target, data)
    _set_concepts(db, q, data.concepts)
    db.flush()
    q.latest_version_id = target.id
    return target


def submit(db: Session, q: Question, actor: uuid.UUID) -> QuestionVersion:
    v = db.get(QuestionVersion, q.latest_version_id)
    if v.status != VersionStatus.DRAFT:
        raise Conflict("Only drafts can be submitted for review.", code="not_draft")
    v.status, v.submitted_at = VersionStatus.IN_REVIEW, _now()
    return v


def publish(
    db: Session, q: Question, actor: uuid.UUID, *, note: str | None = None
) -> QuestionVersion:
    v = db.get(QuestionVersion, q.latest_version_id)
    if v.status not in (VersionStatus.IN_REVIEW, VersionStatus.DRAFT):
        raise Conflict(
            "Nothing to publish — the latest version is already live or archived.",
            code="not_publishable",
        )
    if q.archived_at:
        raise Conflict("Restore the question before publishing it.", code="archived")
    if q.published_version_id:
        old = db.get(QuestionVersion, q.published_version_id)
        old.status = VersionStatus.SUPERSEDED
    v.status = VersionStatus.PUBLISHED
    v.reviewed_by, v.reviewed_at, v.review_note = actor, _now(), note
    v.published_at = _now()
    q.published_version_id = v.id
    return v


def reject(db: Session, q: Question, actor: uuid.UUID, note: str) -> QuestionVersion:
    v = db.get(QuestionVersion, q.latest_version_id)
    if v.status != VersionStatus.IN_REVIEW:
        raise Conflict("Only questions in review can be sent back.", code="not_in_review")
    v.status, v.reviewed_by, v.reviewed_at, v.review_note = (
        VersionStatus.REJECTED,
        actor,
        _now(),
        note,
    )
    return v


def archive(db: Session, q: Question) -> None:
    q.archived_at = q.archived_at or _now()


def restore(db: Session, q: Question) -> None:
    q.archived_at = None


def status_of(q: Question, latest: QuestionVersion) -> str:
    if q.archived_at:
        return "archived"
    if latest.status in (VersionStatus.DRAFT, VersionStatus.IN_REVIEW, VersionStatus.REJECTED):
        return (
            latest.status.value
            if not q.published_version_id
            else (f"published_with_{latest.status.value}")
        )
    return "published" if q.published_version_id else latest.status.value


def get_or_404(db: Session, qid: uuid.UUID) -> Question:
    q = db.get(Question, qid)
    if q is None:
        raise NotFound("Question not found.")
    return q


def version_dict(v: QuestionVersion) -> dict:
    return {
        "id": v.id,
        "version": v.version,
        "status": v.status.value,
        "type": v.type.value,
        "difficulty": v.difficulty,
        "stem": v.stem,
        "content": v.content,
        "answer": v.answer,
        "solution": v.solution,
        "hints": v.hints,
        "estimated_seconds": v.estimated_seconds,
        "source": v.source,
        "created_at": v.created_at,
        "submitted_at": v.submitted_at,
        "reviewed_at": v.reviewed_at,
        "review_note": v.review_note,
        "published_at": v.published_at,
    }


def detail(db: Session, q: Question) -> dict:
    from app.modules.curriculum.service import concept_context

    versions = list(
        db.scalars(
            select(QuestionVersion)
            .where(QuestionVersion.question_id == q.id)
            .order_by(QuestionVersion.version.desc())
        )
    )
    latest = next(v for v in versions if v.id == q.latest_version_id)
    ctx = concept_context(db, [c.concept_id for c in q.concepts])
    attempts = _attempt_counts(db, [q.id]).get(q.id, (0, 0))
    return {
        "id": q.id,
        "status": status_of(q, latest),
        "is_sample": q.is_sample,
        "published_version_id": q.published_version_id,
        "latest": version_dict(latest),
        "versions": [
            {
                "id": v.id,
                "version": v.version,
                "status": v.status.value,
                "created_at": v.created_at,
                "published_at": v.published_at,
                "review_note": v.review_note,
            }
            for v in versions
        ],
        "concepts": [
            {**ctx.get(c.concept_id, {"id": c.concept_id, "name": "?"}), "weight": c.weight}
            for c in q.concepts
        ],
        "archived_at": q.archived_at,
        "created_at": q.created_at,
        "attempts": attempts[0],
        "correct_rate": (attempts[1] / attempts[0]) if attempts[0] else None,
    }


def _attempt_counts(db: Session, qids) -> dict:
    from app.modules.practice.models import QuestionAttempt

    if not qids:
        return {}
    rows = db.execute(
        select(
            QuestionAttempt.question_id,
            func.count(),
            func.count().filter(QuestionAttempt.is_correct.is_(True)),
        )
        .where(QuestionAttempt.question_id.in_(qids))
        .group_by(QuestionAttempt.question_id)
    ).all()
    return {r[0]: (r[1], r[2]) for r in rows}


def list_questions(
    db: Session,
    *,
    status=None,
    concept_id=None,
    qtype=None,
    q=None,
    difficulty=None,
    page=1,
    page_size=20,
) -> tuple[list[dict], int]:
    stmt = select(Question, QuestionVersion).join(
        QuestionVersion, QuestionVersion.id == Question.latest_version_id
    )
    if concept_id:
        stmt = stmt.where(
            Question.id.in_(
                select(QuestionConcept.question_id).where(QuestionConcept.concept_id == concept_id)
            )
        )
    if qtype:
        stmt = stmt.where(QuestionVersion.type == qtype)
    if difficulty:
        stmt = stmt.where(QuestionVersion.difficulty == difficulty)
    if q:
        stmt = stmt.where(
            or_(QuestionVersion.stem.ilike(f"%{q}%"), QuestionVersion.source.ilike(f"%{q}%"))
        )
    if status == "archived":
        stmt = stmt.where(Question.archived_at.is_not(None))
    else:
        stmt = stmt.where(Question.archived_at.is_(None))
        if status == "published":
            stmt = stmt.where(Question.published_version_id.is_not(None))
        elif status in ("draft", "in_review", "rejected"):
            stmt = stmt.where(QuestionVersion.status == status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(
        stmt.order_by(Question.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    from app.modules.curriculum.service import concept_context

    ctx = concept_context(db, {c.concept_id for qq, _ in rows for c in qq.concepts})
    counts = _attempt_counts(db, [qq.id for qq, _ in rows])
    items = [
        {
            "id": qq.id,
            "status": status_of(qq, v),
            "type": v.type.value,
            "difficulty": v.difficulty,
            "stem": v.stem,
            "version": v.version,
            "is_sample": qq.is_sample,
            "concepts": [ctx[c.concept_id]["name"] for c in qq.concepts if c.concept_id in ctx],
            "attempts": counts.get(qq.id, (0, 0))[0],
            "updated_at": v.created_at,
        }
        for qq, v in rows
    ]
    return items, total


def bank_stats(db: Session) -> dict:
    total = (
        db.scalar(select(func.count()).select_from(Question).where(Question.archived_at.is_(None)))
        or 0
    )
    published = (
        db.scalar(
            select(func.count())
            .select_from(Question)
            .where(Question.archived_at.is_(None), Question.published_version_id.is_not(None))
        )
        or 0
    )
    in_review = (
        db.scalar(
            select(func.count())
            .select_from(Question)
            .join(QuestionVersion, QuestionVersion.id == Question.latest_version_id)
            .where(
                Question.archived_at.is_(None), QuestionVersion.status == VersionStatus.IN_REVIEW
            )
        )
        or 0
    )
    return {
        "questions_total": total,
        "questions_published": published,
        "approval_backlog": in_review,
    }


# ── student-facing ───────────────────────────────────────────────────────────


def student_view(v: QuestionVersion, *, hints_revealed: int = 0) -> dict:
    """Everything a student may see *before* answering. No answer key, no solution."""
    return {
        "version_id": v.id,
        "type": v.type.value,
        "difficulty": v.difficulty,
        "stem": v.stem,
        "content": evaluation.student_content(v.type, v.content),
        "estimated_seconds": v.estimated_seconds,
        "hints_available": len(v.hints),
        "hints": v.hints[:hints_revealed],
    }


def published_candidates(db: Session, concept_ids) -> list[tuple[Question, QuestionVersion]]:
    if not concept_ids:
        return []
    return list(
        db.execute(
            select(Question, QuestionVersion)
            .join(QuestionVersion, QuestionVersion.id == Question.published_version_id)
            .where(
                Question.archived_at.is_(None),
                Question.id.in_(
                    select(QuestionConcept.question_id).where(
                        QuestionConcept.concept_id.in_(list(concept_ids))
                    )
                ),
            )
        ).all()
    )


def published_counts(db: Session, concept_ids) -> dict[int, int]:
    if not concept_ids:
        return {}
    rows = db.execute(
        select(QuestionConcept.concept_id, func.count())
        .join(Question, Question.id == QuestionConcept.question_id)
        .where(
            Question.archived_at.is_(None),
            Question.published_version_id.is_not(None),
            QuestionConcept.concept_id.in_(list(concept_ids)),
        )
        .group_by(QuestionConcept.concept_id)
    ).all()
    return dict(rows)
