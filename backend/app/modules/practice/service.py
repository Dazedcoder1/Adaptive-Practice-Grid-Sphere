"""Practice engine: session lifecycle, adaptive delivery, server-side evaluation.

Answer submission (design §7.2):
1. validate ownership, session state and that this is the delivered, unanswered question
2. idempotency: a retried submission returns the original result, never a second attempt
3. evaluate on the server (the browser never decides correctness)
4. save the attempt, update session progress, and write a QuestionAnswered outbox event —
   all in ONE transaction, so an acknowledged answer can't be lost
5. mastery, revision and the error notebook update from that event (in-process in
   development, or by Celery workers)
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.adaptive.selection import (
    Candidate,
    ConceptState,
    SelectionInput,
    select_diagnostic,
    select_next,
)
from app.modules.curriculum import service as curriculum
from app.modules.knowledge_model import service as knowledge
from app.modules.practice.models import (
    Evaluation,
    PracticeSession,
    QuestionAttempt,
    SessionMode,
    SessionQuestion,
    SessionStatus,
)
from app.modules.question_bank import evaluation as ev
from app.modules.question_bank import service as qbank
from app.modules.question_bank.models import Question, QuestionVersion
from app.modules.revision import service as revision
from app.shared.events import EventType, emit
from app.shared.exceptions import AppError, Conflict, NotFound

MAX_SECONDS_PER_QUESTION = 30 * 60  # idle time beyond this doesn't count as study time
DEFAULT_COUNT = 10
MAX_DIAGNOSTIC = 12


def _now() -> datetime:
    return datetime.now(UTC)


def get_owned(
    db: Session, student_id: uuid.UUID, session_id: uuid.UUID, *, lock: bool = False
) -> PracticeSession:
    stmt = select(PracticeSession).where(PracticeSession.id == session_id)
    if lock:
        stmt = stmt.with_for_update()
    s = db.scalar(stmt)
    if s is None or s.student_id != student_id:  # object-level authorisation
        raise NotFound("Practice session not found.")
    return s


# ── creating a session ───────────────────────────────────────────────────────


def create_session(
    db: Session,
    student_id: uuid.UUID,
    *,
    mode: SessionMode,
    subject_id: int | None = None,
    chapter_id: int | None = None,
    topic_id: int | None = None,
    concept_ids: list[int] | None = None,
    question_ids: list[uuid.UUID] | None = None,
    count: int | None = None,
) -> PracticeSession:
    title_parts: list[str] = []
    scope: dict = {}
    if mode == SessionMode.REVIEW:
        if not question_ids:
            raise AppError("Choose questions to re-attempt.", code="empty_scope")
        ids = list(dict.fromkeys(question_ids))[:30]
        attempted = set(
            db.scalars(
                select(QuestionAttempt.question_id).where(
                    QuestionAttempt.student_id == student_id, QuestionAttempt.question_id.in_(ids)
                )
            )
        )
        live = {q.id for q, _ in qbank.published_candidates(db, _concepts_of_questions(db, ids))}
        ids = [q for q in ids if q in attempted and q in live]
        if not ids:
            raise AppError("Those questions aren't available to re-attempt.", code="empty_scope")
        scope = {"question_ids": [str(q) for q in ids]}
        target, title = len(ids), "Mistake review"
    else:
        if mode == SessionMode.REVISION:
            cids = revision.due_concept_ids(db, student_id, limit=10)
            if not cids:
                raise AppError("Nothing is due for revision right now.", code="nothing_due")
            title = "Revision"
        elif concept_ids:
            cids = list(dict.fromkeys(concept_ids))
            ctx = curriculum.concept_context(db, cids)
            if len(ctx) != len(cids):
                raise NotFound("One or more concepts don't exist.")
            title_parts = [ctx[c]["name"] for c in cids][:2]
            title = ", ".join(title_parts) + ("…" if len(cids) > 2 else "")
        elif topic_id or chapter_id or subject_id:
            cids = curriculum.concept_ids_for(
                db, subject_id=subject_id, chapter_id=chapter_id, topic_id=topic_id
            )
            from app.modules.curriculum.models import Chapter, Subject, Topic

            node = (
                db.get(Topic, topic_id)
                if topic_id
                else db.get(Chapter, chapter_id)
                if chapter_id
                else db.get(Subject, subject_id)
            )
            if node is None:
                raise NotFound("That part of the curriculum doesn't exist.")
            title = node.name
        else:
            raise AppError("Choose a subject, chapter or concepts to practise.", code="empty_scope")
        counts = qbank.published_counts(db, cids)
        cids = [c for c in cids if counts.get(c)]
        if not cids:
            raise AppError("There are no published questions for this yet.", code="no_questions")
        scope = {
            "concept_ids": cids,
            "subject_id": subject_id,
            "chapter_id": chapter_id,
            "topic_id": topic_id,
        }
        if mode == SessionMode.DIAGNOSTIC:
            target = min(len(cids), MAX_DIAGNOSTIC)
            title = f"Diagnostic: {title}"
        else:
            available = sum(counts[c] for c in cids)
            target = max(1, min(count or DEFAULT_COUNT, 30, available))
    s = PracticeSession(
        student_id=student_id, mode=mode, scope=scope, title=title[:200], target_count=target
    )
    db.add(s)
    db.flush()
    emit(
        db,
        EventType.PRACTICE_STARTED,
        "practice_session",
        s.id,
        {"student_id": str(student_id), "mode": mode.value},
    )
    return s


def _concepts_of_questions(db: Session, qids) -> list[int]:
    from app.modules.question_bank.models import QuestionConcept

    return list(
        db.scalars(
            select(QuestionConcept.concept_id)
            .where(QuestionConcept.question_id.in_(list(qids)))
            .distinct()
        )
    )


# ── delivering the next question ─────────────────────────────────────────────


def _pending(db: Session, s: PracticeSession) -> SessionQuestion | None:
    return db.scalar(
        select(SessionQuestion).where(
            SessionQuestion.session_id == s.id, SessionQuestion.attempt_id.is_(None)
        )
    )


def _delivered(db: Session, s: PracticeSession) -> list[SessionQuestion]:
    return list(
        db.scalars(
            select(SessionQuestion)
            .where(SessionQuestion.session_id == s.id)
            .order_by(SessionQuestion.position)
        )
    )


def next_question(db: Session, student_id: uuid.UUID, session_id: uuid.UUID) -> dict:
    s = get_owned(db, student_id, session_id, lock=True)
    if s.status == SessionStatus.PAUSED:
        raise Conflict("This session is paused. Resume it to continue.", code="paused")
    if s.status == SessionStatus.COMPLETED:
        return {"finished": True, "session": session_summary(s)}
    pending = _pending(db, s)
    if pending:  # recovery: same question again after a refresh or a dropped connection
        return delivery(db, s, pending)
    if s.answered_count >= s.target_count:
        _complete(s)
        return {"finished": True, "session": session_summary(s)}

    delivered = _delivered(db, s)
    decision = _decide(db, s, delivered)
    if decision is None:  # ran out of questions in scope
        _complete(s)
        return {"finished": True, "session": session_summary(s), "exhausted": True}
    cand, concept_id, reason = decision
    sq = SessionQuestion(
        session_id=s.id,
        position=len(delivered) + 1,
        question_id=uuid.UUID(cand.question_id),
        question_version_id=uuid.UUID(cand.version_id),
        target_concept_id=concept_id,
        selection=reason,
        delivered_at=_now(),
    )
    db.add(sq)
    s.last_activity_at = _now()
    db.flush()
    return delivery(db, s, sq)


def _decide(db: Session, s: PracticeSession, delivered: list[SessionQuestion]):
    if s.mode == SessionMode.REVIEW:
        used = {sq.question_id for sq in delivered}
        for qid in s.scope["question_ids"]:
            q = db.get(Question, uuid.UUID(qid))
            if q.id not in used and q.published_version_id and not q.archived_at:
                cand = Candidate(str(q.id), str(q.published_version_id), 0, ())
                return cand, None, {"rule": "review", "question_id": qid}
        return None

    cids = s.scope["concept_ids"]
    rows = qbank.published_candidates(db, cids)
    candidates = [
        Candidate(str(q.id), str(v.id), v.difficulty, tuple(c.concept_id for c in q.concepts))
        for q, v in rows
    ]
    mastery = knowledge.mastery_map(db, s.student_id)
    states = {
        cid: ConceptState(m.p_known, m.attempts, m.last_practiced_at) for cid, m in mastery.items()
    }
    attempts = {sq.attempt_id: sq for sq in delivered if sq.attempt_id}
    results: dict[int, list[bool]] = {}
    if attempts:
        for a in db.scalars(
            select(QuestionAttempt)
            .where(QuestionAttempt.id.in_(list(attempts)))
            .order_by(QuestionAttempt.created_at)
        ):
            cid = attempts[a.id].target_concept_id
            if cid is not None:
                results.setdefault(cid, []).append(a.is_correct)
    last_seen = (
        dict(
            db.execute(
                select(QuestionAttempt.question_id, func.max(QuestionAttempt.created_at))
                .where(
                    QuestionAttempt.student_id == s.student_id,
                    QuestionAttempt.question_id.in_([uuid.UUID(c.question_id) for c in candidates]),
                )
                .group_by(QuestionAttempt.question_id)
            ).all()
        )
        if candidates
        else {}
    )
    inp = SelectionInput(
        seed=f"{s.id}:{len(delivered) + 1}",
        scope_concepts=cids,
        candidates=candidates,
        mastery=states,
        prerequisites=curriculum.prerequisites_map(db, cids),
        session_question_ids={str(sq.question_id) for sq in delivered},
        recent_concepts=[sq.target_concept_id for sq in delivered if sq.target_concept_id],
        recent_results=results,
        last_seen={str(k): v for k, v in last_seen.items()},
        now=_now(),
    )
    d = select_diagnostic(inp) if s.mode == SessionMode.DIAGNOSTIC else select_next(inp)
    return None if d is None else (d.candidate, d.concept_id, d.reason)


def delivery(db: Session, s: PracticeSession, sq: SessionQuestion) -> dict:
    v = db.get(QuestionVersion, sq.question_version_id)
    q = db.get(Question, sq.question_id)
    ctx = curriculum.concept_context(db, [c.concept_id for c in q.concepts])
    return {
        "finished": False,
        "session": session_summary(s),
        "session_question_id": sq.id,
        "position": sq.position,
        "question": {
            **qbank.student_view(v, hints_revealed=sq.hints_revealed),
            "question_id": q.id,
            "concepts": [{"id": c, "name": ctx[c]["name"]} for c in ctx],
        },
        "why": explain(sq.selection, _with_target(db, ctx, sq.selection)),
        "delivered_at": sq.delivered_at,
    }


def _with_target(db: Session, ctx: dict, reason: dict) -> dict:
    target = reason.get("for_concept_id")
    if target is None or target in ctx:
        return ctx
    return {**ctx, **curriculum.concept_context(db, [target])}


def explain(reason: dict, ctx: dict) -> str:
    """Plain-language reason for the student (the structured reason is stored too)."""
    rule = reason.get("rule")
    name = ctx.get(reason.get("concept_id"), {}).get("name", "this concept")
    target = ctx.get(reason.get("for_concept_id"), {}).get("name")
    if rule == "prerequisite_remediation":
        return f"Strengthening {name} first — {target or 'what you are learning'} builds on it."
    if rule == "prerequisite_first":
        return f"Starting with {name} — {target or 'the next concept'} builds on it."
    if rule == "exploration":
        return f"A quick check on {name} to keep your practice varied."
    if rule == "diagnostic":
        return f"Diagnostic: finding your starting point on {name}."
    if rule == "review":
        return "Re-attempting a question you missed before."
    m = reason.get("mastery")
    if m is None:
        return f"Starting {name} — you haven't practised it yet."
    return f"Practising {name}, where your mastery estimate is {round(m * 100)}%."


def reveal_hint(
    db: Session, student_id: uuid.UUID, session_id: uuid.UUID, sq_id: uuid.UUID
) -> dict:
    s = get_owned(db, student_id, session_id, lock=True)
    sq = db.get(SessionQuestion, sq_id)
    if sq is None or sq.session_id != s.id:
        raise NotFound("Question not found in this session.")
    if sq.attempt_id:
        raise Conflict("You've already answered this question.", code="already_answered")
    v = db.get(QuestionVersion, sq.question_version_id)
    if sq.hints_revealed >= len(v.hints):
        raise AppError("No more hints for this question.", code="no_more_hints")
    sq.hints_revealed += 1
    return {"hints": v.hints[: sq.hints_revealed], "hints_available": len(v.hints)}


def tutor_context(db: Session, student_id: uuid.UUID, sq_id: uuid.UUID) -> dict:
    """What the AI tutor may know about a delivered question (object-level checked).

    Before the student answers: the question as they see it and the hints they've opened —
    never the answer key or solution. After answering: their response, the evaluation,
    the correct answer and the worked solution.
    """
    sq = db.get(SessionQuestion, sq_id)
    if sq is None:
        raise NotFound("Question not found.")
    s = get_owned(db, student_id, sq.session_id)
    v = db.get(QuestionVersion, sq.question_version_id)
    q = db.get(Question, sq.question_id)
    out = {
        "session_question_id": sq.id,
        "session_id": s.id,
        "session_active": s.status == SessionStatus.ACTIVE,
        "question_id": q.id,
        "type": v.type.value,
        "stem": v.stem,
        "content": ev.student_content(v.type, v.content),
        "hints_shown": v.hints[: sq.hints_revealed],
        "hints_remaining": max(len(v.hints) - sq.hints_revealed, 0),
        "concept_ids": [c.concept_id for c in q.concepts],
        "target_concept_id": sq.target_concept_id,
        "answered": sq.attempt_id is not None,
        # Server-side only: lets the tutor's output check catch a leaked answer.
        "_answer_key": v.answer,
    }
    if sq.attempt_id:
        a = db.get(QuestionAttempt, sq.attempt_id)
        result = ev.evaluate(v.type, v.content, v.answer, a.response)
        out.update(
            response=a.response,
            evaluation=a.evaluation.value,
            correct_answer=result.correct_answer,
            solution=v.solution,
        )
    return out


def record_tutor_assist(db: Session, student_id: uuid.UUID, sq_id: uuid.UUID) -> None:
    sq = db.scalar(select(SessionQuestion).where(SessionQuestion.id == sq_id).with_for_update())
    if sq is None or sq.attempt_id is not None:
        return
    get_owned(db, student_id, sq.session_id)
    sq.tutor_assists += 1


# ── submitting an answer ─────────────────────────────────────────────────────


def submit_answer(
    db: Session, student_id: uuid.UUID, sq_id: uuid.UUID, response: dict, idempotency_key: str
) -> tuple[QuestionAttempt, list[uuid.UUID], bool]:
    """Returns (attempt, outbox event ids, replayed). Caller commits."""
    existing = db.scalar(
        select(QuestionAttempt).where(
            QuestionAttempt.student_id == student_id,
            QuestionAttempt.idempotency_key == idempotency_key,
        )
    )
    if existing:
        if existing.session_question_id != sq_id:
            raise Conflict(
                "This idempotency key was used for a different question.",
                code="idempotency_mismatch",
            )
        return existing, [], True

    sq = db.scalar(select(SessionQuestion).where(SessionQuestion.id == sq_id).with_for_update())
    if sq is None:
        raise NotFound("Question not found.")
    s = get_owned(db, student_id, sq.session_id, lock=True)
    if s.status != SessionStatus.ACTIVE:
        raise Conflict("This session isn't active.", code="session_not_active")
    if sq.attempt_id:
        raise Conflict("You've already answered this question.", code="already_answered")

    v = db.get(QuestionVersion, sq.question_version_id)
    try:
        result = ev.evaluate(v.type, v.content, v.answer, response)
    except ev.InvalidResponse as e:
        raise AppError(str(e), code="invalid_response") from e

    now = _now()
    taken = int(min(max((now - sq.delivered_at).total_seconds(), 0), MAX_SECONDS_PER_QUESTION))
    previous = (
        db.scalar(
            select(func.count())
            .select_from(QuestionAttempt)
            .where(
                QuestionAttempt.student_id == student_id,
                QuestionAttempt.question_id == sq.question_id,
            )
        )
        or 0
    )
    attempt = QuestionAttempt(
        student_id=student_id,
        session_id=s.id,
        session_question_id=sq.id,
        question_id=sq.question_id,
        question_version_id=v.id,
        idempotency_key=idempotency_key,
        response=response,
        evaluation=Evaluation(result.evaluation),
        is_correct=result.is_correct,
        score=result.score,
        time_taken_seconds=taken,
        hints_used=sq.hints_revealed + min(sq.tutor_assists, 2),
        difficulty_at_delivery=v.difficulty,
        attempt_number=previous + 1,
        created_at=now,
    )
    db.add(attempt)
    try:
        db.flush()
    except IntegrityError as e:  # concurrent duplicate of the same key
        raise Conflict("This answer was already submitted.", code="duplicate_submission") from e
    sq.attempt_id = attempt.id
    s.answered_count += 1
    s.correct_count += 1 if result.is_correct else 0
    s.active_seconds += taken
    s.last_activity_at = now
    if s.answered_count >= s.target_count:
        _complete(s)

    q = db.get(Question, sq.question_id)
    event = emit(
        db,
        EventType.QUESTION_ANSWERED,
        "question_attempt",
        attempt.id,
        {
            "attempt_id": str(attempt.id),
            "student_id": str(student_id),
            "session_id": str(s.id),
            "question_id": str(q.id),
            "question_type": v.type.value,
            "evaluation": result.evaluation,
            "score": result.score,
            "hints_used": attempt.hints_used,
            "concepts": [[c.concept_id, c.weight] for c in q.concepts],
            "answered_at": now.isoformat(),
        },
    )
    db.flush()
    return attempt, [event.id], False


def feedback(db: Session, attempt: QuestionAttempt) -> dict:
    v = db.get(QuestionVersion, attempt.question_version_id)
    s = db.get(PracticeSession, attempt.session_id)
    result = ev.evaluate(v.type, v.content, v.answer, attempt.response)
    changes = knowledge.changes_for_attempt(db, attempt.id)
    ctx = curriculum.concept_context(db, [c.concept_id for c in changes])
    return {
        "attempt_id": attempt.id,
        "evaluation": attempt.evaluation.value,
        "score": attempt.score,
        "correct_answer": result.correct_answer,
        "solution": v.solution,
        "time_taken_seconds": attempt.time_taken_seconds,
        "mastery_changes": [
            {
                "concept_id": c.concept_id,
                "name": ctx.get(c.concept_id, {}).get("name"),
                "before": round(c.p_before, 4),
                "after": round(c.p_after, 4),
            }
            for c in changes
        ],
        "mastery_pending": not changes and attempt.evaluation != Evaluation.UNGRADED,
        "session": session_summary(s),
    }


# ── lifecycle ────────────────────────────────────────────────────────────────


def _complete(s: PracticeSession) -> None:
    if s.status != SessionStatus.COMPLETED:
        s.status, s.completed_at = SessionStatus.COMPLETED, _now()


def set_status(
    db: Session, student_id: uuid.UUID, session_id: uuid.UUID, action: str
) -> PracticeSession:
    s = get_owned(db, student_id, session_id, lock=True)
    if s.status == SessionStatus.COMPLETED:
        raise Conflict("This session is already complete.", code="completed")
    if action == "pause":
        s.status = SessionStatus.PAUSED
    elif action == "resume":
        s.status = SessionStatus.ACTIVE
        pending = _pending(db, s)
        if pending:  # time spent paused doesn't count against the question
            pending.delivered_at = _now()
    elif action == "complete":
        _complete(s)
        pending = _pending(db, s)
        if pending:
            db.delete(pending)  # never answered → not part of the record
    s.last_activity_at = _now()
    return s


def session_summary(s: PracticeSession) -> dict:
    return {
        "id": s.id,
        "mode": s.mode.value,
        "status": s.status.value,
        "title": s.title,
        "target_count": s.target_count,
        "answered_count": s.answered_count,
        "correct_count": s.correct_count,
        "active_seconds": s.active_seconds,
        "created_at": s.created_at,
        "completed_at": s.completed_at,
        "last_activity_at": s.last_activity_at,
    }


def list_sessions(
    db: Session, student_id: uuid.UUID, *, status: str | None = None, limit: int = 20
) -> list[dict]:
    stmt = select(PracticeSession).where(PracticeSession.student_id == student_id)
    if status == "open":
        stmt = stmt.where(PracticeSession.status != SessionStatus.COMPLETED)
    elif status:
        stmt = stmt.where(PracticeSession.status == status)
    return [
        session_summary(s)
        for s in db.scalars(stmt.order_by(PracticeSession.last_activity_at.desc()).limit(limit))
    ]


def report(db: Session, student_id: uuid.UUID, session_id: uuid.UUID) -> dict:
    from app.modules.knowledge_model import bkt
    from app.modules.knowledge_model.models import MasteryHistory

    s = get_owned(db, student_id, session_id)
    rows = db.execute(
        select(SessionQuestion, QuestionAttempt, QuestionVersion)
        .join(QuestionAttempt, QuestionAttempt.id == SessionQuestion.attempt_id)
        .join(QuestionVersion, QuestionVersion.id == QuestionAttempt.question_version_id)
        .where(SessionQuestion.session_id == s.id)
        .order_by(SessionQuestion.position)
    ).all()
    attempt_ids = [a.id for _, a, _ in rows]
    history = (
        list(
            db.scalars(
                select(MasteryHistory)
                .where(MasteryHistory.attempt_id.in_(attempt_ids))
                .order_by(MasteryHistory.created_at)
            )
        )
        if attempt_ids
        else []
    )
    per_concept: dict[int, dict] = {}
    for h in history:
        e = per_concept.setdefault(
            h.concept_id, {"before": h.p_before, "after": h.p_after, "answered": 0}
        )
        e["after"] = h.p_after
        e["answered"] += 1
    current = knowledge.mastery_map(db, student_id, per_concept)
    ctx = curriculum.concept_context(
        db, list(per_concept) + [sq.target_concept_id for sq, _, _ in rows if sq.target_concept_id]
    )
    concepts = []
    for cid, e in per_concept.items():
        m = current.get(cid)
        concepts.append(
            {
                "concept_id": cid,
                "name": ctx.get(cid, {}).get("name"),
                "before": round(e["before"], 4),
                "after": round(e["after"], 4),
                "answered": e["answered"],
                "level": bkt.level(m.p_known, m.attempts) if m else "not_started",
            }
        )
    concepts.sort(key=lambda c: c["after"])
    graded = [a for _, a, _ in rows if a.evaluation != Evaluation.UNGRADED]
    return {
        "session": session_summary(s),
        "accuracy": (sum(a.score for a in graded) / len(graded)) if graded else None,
        "questions": [
            {
                "position": sq.position,
                "stem": v.stem,
                "type": v.type.value,
                "difficulty": v.difficulty,
                "evaluation": a.evaluation.value,
                "score": a.score,
                "time_taken_seconds": a.time_taken_seconds,
                "hints_used": a.hints_used,
                "question_id": a.question_id,
                "concept": ctx.get(sq.target_concept_id, {}).get("name"),
            }
            for sq, a, v in rows
        ],
        "concepts": concepts,
        "weak_concepts": [c for c in concepts if c["level"] in ("weak", "developing")],
        "model_version": bkt.MODEL_VERSION,
    }


def recent_attempts_exist(db: Session, student_id: uuid.UUID, question_id: uuid.UUID) -> bool:
    return (
        db.scalar(
            select(func.count())
            .select_from(QuestionAttempt)
            .where(
                QuestionAttempt.student_id == student_id, QuestionAttempt.question_id == question_id
            )
        )
        > 0
    )
