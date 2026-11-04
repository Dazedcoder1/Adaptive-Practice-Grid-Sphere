"""Student dashboard metrics — every number is computed from the student's real records.

Computed on request from indexed tables for now; move to pre-aggregated tables when attempt
volume makes these queries slow (design §12).
"""

import uuid
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.adaptive import service as adaptive
from app.modules.knowledge_model import bkt
from app.modules.knowledge_model import service as knowledge
from app.modules.practice.models import Evaluation, QuestionAttempt
from app.modules.practice.service import list_sessions
from app.modules.revision import service as revision


def _streak(days: set[date], today: date) -> int:
    start = today if today in days else today - timedelta(days=1)
    n = 0
    while start - timedelta(days=n) in days:
        n += 1
    return n


def dashboard(db: Session, student_id: uuid.UUID) -> dict:
    from app.modules.users.service import get_profile

    profile = get_profile(db, student_id)
    tz = ZoneInfo(profile.timezone if profile else "Asia/Kolkata")
    base = select(QuestionAttempt).where(QuestionAttempt.student_id == student_id)
    graded = base.where(QuestionAttempt.evaluation != Evaluation.UNGRADED)
    attempted = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    graded_n = db.scalar(select(func.count()).select_from(graded.subquery())) or 0
    score_sum = (
        db.scalar(
            select(func.coalesce(func.sum(QuestionAttempt.score), 0)).where(
                QuestionAttempt.student_id == student_id,
                QuestionAttempt.evaluation != Evaluation.UNGRADED,
            )
        )
        or 0
    )
    seconds = (
        db.scalar(
            select(func.coalesce(func.sum(QuestionAttempt.time_taken_seconds), 0)).where(
                QuestionAttempt.student_id == student_id
            )
        )
        or 0
    )
    since = datetime.now(UTC) - timedelta(days=60)
    stamps = db.scalars(
        select(QuestionAttempt.created_at).where(
            QuestionAttempt.student_id == student_id, QuestionAttempt.created_at >= since
        )
    )
    days = {s.astimezone(tz).date() for s in stamps}
    today = datetime.now(tz).date()

    scope = adaptive._scope(db, profile)
    mastery = knowledge.mastery_map(db, student_id, scope or None)
    levels = [bkt.level(m.p_known, m.attempts) for m in mastery.values()]
    q = revision.enriched_queue(db, student_id)
    weak = adaptive.weak_concepts(db, student_id)

    return {
        "has_activity": attempted > 0,
        "questions_attempted": attempted,
        "accuracy": (float(score_sum) / graded_n) if graded_n else None,
        "study_seconds": int(seconds),
        "streak_days": _streak(days, today),
        "active_today": today in days,
        "concepts_total": len(scope),
        "concepts_practised": len(mastery),
        "concepts_mastered": levels.count("mastered"),
        "average_mastery": (sum(m.p_known for m in mastery.values()) / len(mastery))
        if mastery
        else None,
        "revision_due": len(q["due"]),
        "revision_upcoming": q["upcoming"][:5],
        "weak_concepts": weak[:5],
        "recommendations": adaptive.recommendations(db, student_id),
        "recent_sessions": list_sessions(db, student_id, limit=5),
        "model_version": bkt.MODEL_VERSION,
    }
