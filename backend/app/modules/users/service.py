"""Student profiles. Other modules read profiles through these functions."""

import uuid
from datetime import UTC, datetime
from zoneinfo import available_timezones

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.audit import service as audit
from app.modules.users.models import StudentProfile
from app.shared.exceptions import AppError, NotFound

_TIMEZONES = available_timezones()


def get_profile(db: Session, user_id: uuid.UUID) -> StudentProfile | None:
    return db.scalar(select(StudentProfile).where(StudentProfile.user_id == user_id))


def require_profile(db: Session, user_id: uuid.UUID) -> StudentProfile:
    profile = get_profile(db, user_id)
    if profile is None:
        raise NotFound("Profile not found.")
    return profile


def update_profile(
    db: Session, user_id: uuid.UUID, *, display_name: str | None, timezone: str | None
) -> StudentProfile:
    profile = require_profile(db, user_id)
    if display_name is not None:
        profile.display_name = display_name.strip()
    if timezone is not None:
        if timezone not in _TIMEZONES:
            raise AppError("Unknown timezone.", code="bad_timezone")
        profile.timezone = timezone
    return profile


def request_account_deletion(db: Session, user, ip: str | None) -> datetime:
    """Records the request (DPDP right to erasure). Fulfilment — scrubbing personal data
    while keeping anonymised learning records — is an admin-reviewed workflow."""
    if user.deletion_requested_at is None:
        user.deletion_requested_at = datetime.now(UTC)
        audit.record(
            db,
            "user.deletion_requested",
            actor_user_id=user.id,
            target_type="user",
            target_id=user.id,
            ip=ip,
        )
    return user.deletion_requested_at


def cancel_account_deletion(db: Session, user, ip: str | None) -> None:
    if user.deletion_requested_at is not None:
        user.deletion_requested_at = None
        audit.record(
            db,
            "user.deletion_cancelled",
            actor_user_id=user.id,
            target_type="user",
            target_id=user.id,
            ip=ip,
        )


# ── onboarding ───────────────────────────────────────────────────────────────

GOALS = {
    "board_exam": "Score well in my board exams",
    "competitive_exam": "Prepare for a competitive exam",
    "strengthen_basics": "Strengthen my basics",
    "keep_up": "Keep up with school lessons",
    "get_ahead": "Get ahead of my class",
}


def save_onboarding(
    db: Session,
    user_id: uuid.UUID,
    *,
    study_mode: str,
    curriculum_id: int,
    subject_ids: list[int],
    goals: list[str],
    target_exam_date,
    weekly_days: int | None,
    minutes_per_day: int | None,
) -> StudentProfile:
    from app.modules.curriculum.models import ContentStatus, Curriculum, Subject

    profile = require_profile(db, user_id)
    cur = db.get(Curriculum, curriculum_id)
    if cur is None or cur.status != ContentStatus.PUBLISHED:
        raise AppError("Choose an available curriculum.", code="bad_curriculum")
    if cur.board.study_mode.value != study_mode:
        raise AppError(
            "That curriculum doesn't match the study mode you chose.", code="mode_mismatch"
        )
    valid = set(db.scalars(select(Subject.id).where(Subject.curriculum_id == cur.id)))
    chosen = [s for s in dict.fromkeys(subject_ids) if s in valid]
    if not chosen:
        raise AppError("Choose at least one subject.", code="no_subjects")
    bad_goals = [g for g in goals if g not in GOALS]
    if bad_goals:
        raise AppError(f"Unknown goal(s): {bad_goals}", code="bad_goal")
    profile.study_mode = study_mode
    profile.curriculum_id = cur.id
    profile.target_exam_date = target_exam_date
    profile.preferences = {
        **(profile.preferences or {}),
        "subject_ids": chosen,
        "goals": list(dict.fromkeys(goals)),
        # A preference only — the platform never forces a timetable.
        "schedule": {"weekly_days": weekly_days, "minutes_per_day": minutes_per_day},
    }
    profile.onboarding_completed = True
    return profile
