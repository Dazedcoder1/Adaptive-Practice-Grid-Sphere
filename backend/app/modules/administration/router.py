"""/api/v1/admin — Super Admin portal APIs. Every route checks a specific permission."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.config.database import DbSession, transaction
from app.modules.administration import service
from app.modules.administration.schemas import (
    AdminUserDetail,
    AdminUserRow,
    AuditLogOut,
    DeadLetterOut,
    LoginEventOut,
    Page,
    PlatformStats,
    RoleOut,
    StatusChange,
)
from app.modules.identity import service as identity
from app.modules.identity.models import User, UserStatus
from app.shared.exceptions import NotFound
from app.shared.permissions import Principal, require_permission
from app.shared.request import client_ip

router = APIRouter(prefix="/admin", tags=["admin"])

PageNo = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]


def perm(code: str):
    return Annotated[Principal, Depends(require_permission(code))]


@router.get("/stats", response_model=PlatformStats)
def stats(_: perm("analytics.read"), db: DbSession):
    return service.platform_stats(db)


@router.get("/users", response_model=Page[AdminUserRow])
def list_users(
    _: perm("users.read"),
    db: DbSession,
    q: Annotated[str | None, Query(max_length=100)] = None,
    status: UserStatus | None = None,
    role: Annotated[str | None, Query(max_length=32)] = None,
    deletion_requested: bool | None = None,
    page: PageNo = 1,
    page_size: PageSize = 20,
):
    items, total = service.list_users(
        db,
        q=q,
        status=status,
        role=role,
        deletion_requested=deletion_requested,
        page=page,
        page_size=page_size,
    )
    return Page(items=items, total=total, page=page, page_size=page_size)


def _get_user(db, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise NotFound("User not found.")
    return user


@router.get("/users/{user_id}", response_model=AdminUserDetail)
def get_user(user_id: uuid.UUID, _: perm("users.read"), db: DbSession):
    return service.user_detail(db, _get_user(db, user_id))


@router.post("/users/{user_id}/suspend", response_model=AdminUserDetail)
def suspend_user(
    user_id: uuid.UUID,
    body: StatusChange,
    request: Request,
    p: perm("users.manage"),
    db: DbSession,
):
    with transaction(db):
        identity.set_status(
            db,
            p.user_id,
            _get_user(db, user_id),
            UserStatus.SUSPENDED,
            body.reason,
            client_ip(request),
        )
    return service.user_detail(db, _get_user(db, user_id))


@router.post("/users/{user_id}/activate", response_model=AdminUserDetail)
def activate_user(
    user_id: uuid.UUID,
    body: StatusChange,
    request: Request,
    p: perm("users.manage"),
    db: DbSession,
):
    with transaction(db):
        identity.set_status(
            db,
            p.user_id,
            _get_user(db, user_id),
            UserStatus.ACTIVE,
            body.reason,
            client_ip(request),
        )
    return service.user_detail(db, _get_user(db, user_id))


@router.get("/roles", response_model=list[RoleOut])
def roles(_: perm("users.read"), db: DbSession):
    return service.list_roles(db)


@router.get("/audit-logs", response_model=Page[AuditLogOut])
def audit_logs(
    _: perm("audit.read"),
    db: DbSession,
    action: Annotated[str | None, Query(max_length=64)] = None,
    actor_user_id: uuid.UUID | None = None,
    target_id: Annotated[str | None, Query(max_length=64)] = None,
    page: PageNo = 1,
    page_size: PageSize = 50,
):
    items, total = service.list_audit_logs(
        db,
        action=action,
        actor_user_id=actor_user_id,
        target_id=target_id,
        page=page,
        page_size=page_size,
    )
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/login-events", response_model=Page[LoginEventOut])
def login_events(
    _: perm("audit.read"),
    db: DbSession,
    success: bool | None = None,
    email: Annotated[str | None, Query(max_length=320)] = None,
    page: PageNo = 1,
    page_size: PageSize = 50,
):
    items, total = service.list_login_events(
        db, success=success, email=email, page=page, page_size=page_size
    )
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/dead-letters", response_model=Page[DeadLetterOut])
def dead_letters(
    _: perm("settings.manage"), db: DbSession, page: PageNo = 1, page_size: PageSize = 50
):
    items, total = service.list_dead_letters(db, page, page_size)
    return Page(items=items, total=total, page=page, page_size=page_size)
