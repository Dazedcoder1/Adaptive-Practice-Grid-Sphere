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
