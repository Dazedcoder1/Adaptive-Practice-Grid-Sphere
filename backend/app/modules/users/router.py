"""/api/v1/students — the signed-in student's own profile and account settings."""

from fastapi import APIRouter, Request

from app.config.database import DbSession, transaction
from app.modules.identity.models import User
from app.modules.users import service
from app.modules.users.schemas import DeletionStatus, ProfileOut, ProfileUpdate
from app.shared.permissions import CurrentStudent
from app.shared.request import client_ip

router = APIRouter(prefix="/students", tags=["students"])


def _out(db, user: User) -> ProfileOut:
    p = service.require_profile(db, user.id)
    return ProfileOut(
        user_id=user.id,
        email=user.email,
        display_name=p.display_name,
        timezone=p.timezone,
        is_minor=p.is_minor,
        guardian_email=p.guardian_email,
        onboarding_completed=p.onboarding_completed,
        study_mode=p.study_mode,
        deletion_requested_at=user.deletion_requested_at,
        created_at=user.created_at,
    )


@router.get("/me", response_model=ProfileOut)
def get_me(p: CurrentStudent, db: DbSession):
    return _out(db, db.get(User, p.user_id))


@router.patch("/me", response_model=ProfileOut)
def update_me(body: ProfileUpdate, p: CurrentStudent, db: DbSession):
    with transaction(db):
        service.update_profile(
            db, p.user_id, display_name=body.display_name, timezone=body.timezone
        )
    return _out(db, db.get(User, p.user_id))


@router.post("/me/deletion-request", response_model=DeletionStatus)
def request_deletion(request: Request, p: CurrentStudent, db: DbSession):
    with transaction(db):
        at = service.request_account_deletion(db, db.get(User, p.user_id), client_ip(request))
    return DeletionStatus(
        deletion_requested_at=at,
        message="Deletion requested. An administrator will process it; you can cancel until then.",
    )


@router.delete("/me/deletion-request", response_model=DeletionStatus)
def cancel_deletion(request: Request, p: CurrentStudent, db: DbSession):
    with transaction(db):
        service.cancel_account_deletion(db, db.get(User, p.user_id), client_ip(request))
    return DeletionStatus(deletion_requested_at=None, message="Deletion request cancelled.")
