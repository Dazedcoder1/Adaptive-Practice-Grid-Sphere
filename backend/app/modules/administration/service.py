"""Read models for the Super Admin portal. Mutations go through the owning module's
service (e.g. identity.service.set_status) so business rules stay in one place."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.modules.audit.models import AuditLog
from app.modules.identity.models import AuthSession, Role, User, UserStatus, user_roles
from app.modules.security.models import LoginEvent
from app.modules.users.models import StudentProfile
from app.shared.events import DeadLetter, OutboxEvent


def _count(db: Session, stmt: Select) -> int:
    return db.scalar(select(func.count()).select_from(stmt.subquery())) or 0


def _students() -> Select:
    return (
        select(User.id)
        .join(user_roles, user_roles.c.user_id == User.id)
        .join(Role, Role.id == user_roles.c.role_id)
        .where(Role.name == "student", User.deleted_at.is_(None))
    )


def platform_stats(db: Session) -> dict:
    now = datetime.now(UTC)
    week, day = now - timedelta(days=7), now - timedelta(days=1)
    students = _students()
    return {
        "total_students": _count(db, students),
        "new_registrations_7d": _count(db, students.where(User.created_at >= week)),
        "active_students_7d": _count(
            db,
            select(LoginEvent.user_id)
            .where(
                LoginEvent.success.is_(True),
                LoginEvent.portal == "student",
                LoginEvent.created_at >= week,
            )
            .distinct(),
        ),
        "pending_verification": _count(
            db, students.where(User.status == UserStatus.PENDING_VERIFICATION)
        ),
        "pending_guardian_consent": _count(
            db, students.where(User.status == UserStatus.PENDING_CONSENT)
        ),
        "suspended": _count(db, students.where(User.status == UserStatus.SUSPENDED)),
        "deletion_requests": _count(db, students.where(User.deletion_requested_at.is_not(None))),
        "failed_logins_24h": _count(
            db,
            select(LoginEvent.id).where(
                LoginEvent.success.is_(False), LoginEvent.created_at >= day
            ),
        ),
        "failed_jobs": _count(db, select(DeadLetter.id).where(DeadLetter.replayed_at.is_(None)))
        + _count(db, select(OutboxEvent.id).where(OutboxEvent.dead_lettered_at.is_not(None))),
        "outbox_backlog": _count(
            db,
            select(OutboxEvent.id).where(
                OutboxEvent.published_at.is_(None), OutboxEvent.dead_lettered_at.is_(None)
            ),
        ),
        **_learning_stats(db, week),
        "generated_at": now,
    }


def _learning_stats(db: Session, week) -> dict:
    from app.modules.curriculum.models import Concept
    from app.modules.practice.models import PracticeSession, QuestionAttempt
    from app.modules.question_bank.models import Question, QuestionConcept
    from app.modules.question_bank.service import bank_stats

    concepts = db.scalar(select(func.count()).select_from(Concept)) or 0
    covered = (
        db.scalar(
            select(func.count(func.distinct(QuestionConcept.concept_id)))
            .join(Question, Question.id == QuestionConcept.question_id)
            .where(Question.published_version_id.is_not(None), Question.archived_at.is_(None))
        )
        or 0
    )
    return {
        **bank_stats(db),
        "practice_sessions_7d": _count(
            db, select(PracticeSession.id).where(PracticeSession.created_at >= week)
        ),
        "questions_attempted_7d": _count(
            db, select(QuestionAttempt.id).where(QuestionAttempt.created_at >= week)
        ),
        "concepts_total": concepts,
        "concepts_with_questions": covered,
    }


def _row(user: User, profile: StudentProfile | None) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "display_name": profile.display_name if profile else None,
        "status": user.status.value,
        "roles": user.role_names,
        "is_minor": profile.is_minor if profile else None,
        "created_at": user.created_at,
        "last_login_at": user.last_login_at,
        "deletion_requested_at": user.deletion_requested_at,
    }


def list_users(
    db: Session,
    *,
    q: str | None,
    status: UserStatus | None,
    role: str | None,
    deletion_requested: bool | None,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    stmt = (
        select(User, StudentProfile)
        .outerjoin(StudentProfile, StudentProfile.user_id == User.id)
        .where(User.deleted_at.is_(None))
    )
    if q:
        like = f"%{q.strip().lower()}%"
        stmt = stmt.where(or_(User.email.ilike(like), StudentProfile.display_name.ilike(like)))
    if status:
        stmt = stmt.where(User.status == status)
    if role:
        stmt = stmt.where(
            User.id.in_(
                select(user_roles.c.user_id)
                .join(Role, Role.id == user_roles.c.role_id)
                .where(Role.name == role)
            )
        )
    if deletion_requested is not None:
        stmt = stmt.where(
            User.deletion_requested_at.is_not(None)
            if deletion_requested
            else User.deletion_requested_at.is_(None)
        )
    total = db.scalar(select(func.count()).select_from(stmt.with_only_columns(User.id).subquery()))
    rows = db.execute(
        stmt.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return [_row(u, p) for u, p in rows], total or 0


def _mask(email: str | None) -> str | None:
    if not email or "@" not in email:
        return None
    name, domain = email.split("@", 1)
    return f"{name[:2]}{'•' * max(len(name) - 2, 1)}@{domain}"


def login_event_dict(e: LoginEvent) -> dict:
    return {
        "id": e.id,
        "email": e.email,
        "portal": e.portal,
        "success": e.success,
        "reason": e.reason,
        "ip_address": str(e.ip_address) if e.ip_address else None,
        "user_agent": e.user_agent,
        "created_at": e.created_at,
    }


def user_detail(db: Session, user: User) -> dict:
    profile = db.scalar(select(StudentProfile).where(StudentProfile.user_id == user.id))
    sessions = _count(
        db,
        select(AuthSession.id).where(
            AuthSession.user_id == user.id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > datetime.now(UTC),
        ),
    )
    logins = db.scalars(
        select(LoginEvent)
        .where(LoginEvent.user_id == user.id)
        .order_by(LoginEvent.created_at.desc())
        .limit(10)
    ).all()
    return {
        **_row(user, profile),
        "email_verified_at": user.email_verified_at,
        "suspended_reason": user.suspended_reason,
        "guardian_email_masked": _mask(profile.guardian_email) if profile else None,
        "timezone": profile.timezone if profile else None,
        "active_sessions": sessions,
        "recent_logins": [login_event_dict(e) for e in logins],
    }


def list_audit_logs(
    db: Session,
    *,
    action: str | None,
    actor_user_id: uuid.UUID | None,
    target_id: str | None,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    stmt = select(AuditLog, User.email).outerjoin(User, User.id == AuditLog.actor_user_id)
    if action:
        stmt = stmt.where(AuditLog.action.ilike(f"%{action}%"))
    if actor_user_id:
        stmt = stmt.where(AuditLog.actor_user_id == actor_user_id)
    if target_id:
        stmt = stmt.where(AuditLog.target_id == target_id)
    total = db.scalar(
        select(func.count()).select_from(stmt.with_only_columns(AuditLog.id).subquery())
    )
    rows = db.execute(
        stmt.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    items = [
        {
            "id": a.id,
            "actor_user_id": a.actor_user_id,
            "actor_email": email,
            "action": a.action,
            "target_type": a.target_type,
            "target_id": a.target_id,
            "details": a.details,
            "ip_address": str(a.ip_address) if a.ip_address else None,
            "created_at": a.created_at,
        }
        for a, email in rows
    ]
    return items, total or 0


def list_login_events(
    db: Session, *, success: bool | None, email: str | None, page: int, page_size: int
) -> tuple[list[dict], int]:
    stmt = select(LoginEvent)
    if success is not None:
        stmt = stmt.where(LoginEvent.success.is_(success))
    if email:
        stmt = stmt.where(LoginEvent.email.ilike(f"%{email.strip().lower()}%"))
    total = _count(db, stmt)
    rows = db.scalars(
        stmt.order_by(LoginEvent.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return [login_event_dict(e) for e in rows], total


def list_roles(db: Session) -> list[dict]:
    return [
        {
            "name": r.name,
            "description": r.description,
            "permissions": sorted(p.code for p in r.permissions),
        }
        for r in db.scalars(select(Role).order_by(Role.id))
    ]


def list_dead_letters(db: Session, page: int, page_size: int) -> tuple[list[DeadLetter], int]:
    stmt = select(DeadLetter)
    total = _count(db, stmt)
    rows = db.scalars(
        stmt.order_by(DeadLetter.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return list(rows), total
