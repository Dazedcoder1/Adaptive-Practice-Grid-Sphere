import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int


class PlatformStats(BaseModel):
    """Every number here comes from a live database query."""

    total_students: int
    new_registrations_7d: int
    active_students_7d: int
    pending_verification: int
    pending_guardian_consent: int
    suspended: int
    deletion_requests: int
    failed_logins_24h: int
    failed_jobs: int
    outbox_backlog: int
    generated_at: datetime


class AdminUserRow(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None
    status: str
    roles: list[str]
    is_minor: bool | None
    created_at: datetime
    last_login_at: datetime | None
    deletion_requested_at: datetime | None


class LoginEventOut(BaseModel):
    id: uuid.UUID
    email: str
    portal: str
    success: bool
    reason: str | None
    ip_address: str | None
    user_agent: str | None
    created_at: datetime


class AdminUserDetail(AdminUserRow):
    email_verified_at: datetime | None
    suspended_reason: str | None
    guardian_email_masked: str | None
    timezone: str | None
    active_sessions: int
    recent_logins: list[LoginEventOut]


class StatusChange(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class AuditLogOut(BaseModel):
    id: uuid.UUID
    actor_user_id: uuid.UUID | None
    actor_email: str | None
    action: str
    target_type: str | None
    target_id: str | None
    details: dict[str, Any]
    ip_address: str | None
    created_at: datetime


class RoleOut(BaseModel):
    name: str
    description: str
    permissions: list[str]


class DeadLetterOut(BaseModel):
    id: uuid.UUID
    task_name: str
    event_id: uuid.UUID | None
    error: str
    created_at: datetime
    replayed_at: datetime | None
