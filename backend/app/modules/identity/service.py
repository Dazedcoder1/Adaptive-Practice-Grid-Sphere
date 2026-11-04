"""Identity: registration, verification, guardian consent, login sessions, passwords.

Every function takes the caller's Session and does NOT commit — the router owns the
transaction, so the change, its audit row and its login event commit together.
Emails are returned as callables to send *after* commit (never email about a rollback).
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config.security import (
    create_access_token,
    hash_password,
    hash_token,
    needs_rehash,
    new_opaque_token,
    verify_password,
)
from app.config.settings import settings
from app.integrations.email import send_email
from app.modules.audit import service as audit
from app.modules.identity.models import (
    AuthSession,
    ConsentRecord,
    OneTimeToken,
    Role,
    TokenPurpose,
    User,
    UserStatus,
)
from app.modules.security import service as security
from app.modules.users.models import StudentProfile
from app.shared.events import EventType, emit
from app.shared.exceptions import AppError, Conflict, Forbidden, Unauthorized

STUDENT_ROLE = "student"
ADMIN_ROLE = "super_admin"

PostCommit = Callable[[], None]


def now() -> datetime:
    return datetime.now(UTC)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_active_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(
        select(User).where(User.email == normalize_email(email), User.deleted_at.is_(None))
    )


def _role(db: Session, name: str) -> Role:
    role = db.scalar(select(Role).where(Role.name == name))
    if role is None:
        raise RuntimeError(f"Role {name!r} missing — run `alembic upgrade head`")
    return role


# ── One-time tokens ──────────────────────────────────────────────────────────


def _issue_token(db: Session, user: User, purpose: TokenPurpose, ttl: timedelta) -> str:
    # A new token for the same purpose invalidates older unused ones.
    db.execute(
        update(OneTimeToken)
        .where(
            OneTimeToken.user_id == user.id,
            OneTimeToken.purpose == purpose,
            OneTimeToken.used_at.is_(None),
        )
        .values(used_at=now())
    )
    raw, digest = new_opaque_token()
    db.add(
        OneTimeToken(user_id=user.id, purpose=purpose, token_hash=digest, expires_at=now() + ttl)
    )
    return raw


def _consume_token(db: Session, raw: str, purpose: TokenPurpose) -> User:
    tok = db.scalar(
        select(OneTimeToken)
        .where(OneTimeToken.token_hash == hash_token(raw), OneTimeToken.purpose == purpose)
        .with_for_update()
    )
    if tok is None or tok.used_at is not None or tok.expires_at < now():
        raise AppError("This link is invalid or has expired.", code="invalid_token")
    tok.used_at = now()
    user = db.get(User, tok.user_id)
    if user is None or user.deleted_at is not None:
        raise AppError("This link is invalid or has expired.", code="invalid_token")
    return user


def _link(path: str, token: str) -> str:
    return f"{settings.frontend_url.rstrip('/')}{path}?token={token}"


def _verification_email(user: User, token: str) -> PostCommit:
    link = _link("/verify-email", token)
    return lambda: send_email(
        user.email,
        "Verify your AdaptiveLearn AI email",
        f"Welcome to AdaptiveLearn AI!\n\nConfirm your email address:\n{link}\n\n"
        f"This link expires in {settings.email_token_hours} hours.",
    )


def _guardian_email(guardian: str, student_name: str, token: str) -> PostCommit:
    link = _link("/guardian-consent", token)
    return lambda: send_email(
        guardian,
        f"Consent request for {student_name}'s AdaptiveLearn AI account",
        f"{student_name} has registered for AdaptiveLearn AI and listed you as their parent "
        f"or guardian.\n\nAs they are under 18, we need your consent before their account "
        f"can be used. Review and give consent here:\n{link}\n\n"
        f"If you don't recognise this request, ignore this email and no account will be "
        f"activated.",
    )


# ── Registration & activation ────────────────────────────────────────────────


@dataclass
class RegisterInput:
    email: str
    password: str
    display_name: str
    is_minor: bool
    guardian_email: str | None
    accepted_terms: bool


def register_student(db: Session, data: RegisterInput, ip: str | None) -> tuple[User, PostCommit]:
    email = normalize_email(data.email)
    if not data.accepted_terms:
        raise AppError("You must accept the terms and privacy policy.", code="terms_required")
    if data.is_minor and not data.guardian_email:
        raise AppError("A parent or guardian email is required.", code="guardian_required")
    if data.is_minor and normalize_email(data.guardian_email or "") == email:
        raise AppError(
            "Guardian email must be different from yours.", code="guardian_same_as_student"
        )
    if get_active_user_by_email(db, email):
        raise Conflict("An account with this email already exists.", code="email_taken")

    user = User(email=email, password_hash=hash_password(data.password))
    user.roles = [_role(db, STUDENT_ROLE)]
    db.add(user)
    db.flush()
    db.add(
        StudentProfile(
            user_id=user.id,
            display_name=data.display_name.strip(),
            is_minor=data.is_minor,
            guardian_email=normalize_email(data.guardian_email) if data.is_minor else None,
        )
    )
    for kind in ("terms", "privacy"):
        db.add(
            ConsentRecord(
                user_id=user.id,
                consent_type=kind,
                policy_version=settings.policy_version,
                granted_by="self",
                granted=True,
                ip_address=ip,
            )
        )
    token = _issue_token(
        db, user, TokenPurpose.VERIFY_EMAIL, timedelta(hours=settings.email_token_hours)
    )
    emit(db, EventType.STUDENT_REGISTERED, "user", user.id, {"user_id": str(user.id)})
    audit.record(
        db, "user.registered", actor_user_id=user.id, target_type="user", target_id=user.id, ip=ip
    )
    return user, _verification_email(user, token)


def resend_verification(db: Session, email: str) -> PostCommit | None:
    user = get_active_user_by_email(db, email)
    if user is None or user.status != UserStatus.PENDING_VERIFICATION:
        return None  # same response either way — don't reveal whether the account exists
    token = _issue_token(
        db, user, TokenPurpose.VERIFY_EMAIL, timedelta(hours=settings.email_token_hours)
    )
    return _verification_email(user, token)


def verify_email(db: Session, raw_token: str, ip: str | None) -> tuple[User, PostCommit | None]:
    user = _consume_token(db, raw_token, TokenPurpose.VERIFY_EMAIL)
    user.email_verified_at = user.email_verified_at or now()
    after: PostCommit | None = None
    if user.status == UserStatus.PENDING_VERIFICATION:
        profile = db.scalar(select(StudentProfile).where(StudentProfile.user_id == user.id))
        if profile and profile.is_minor:
            user.status = UserStatus.PENDING_CONSENT
            token = _issue_token(db, user, TokenPurpose.GUARDIAN_CONSENT, timedelta(days=7))
            after = _guardian_email(profile.guardian_email or "", profile.display_name, token)
        else:
            user.status = UserStatus.ACTIVE
    audit.record(
        db,
        "user.email_verified",
        actor_user_id=user.id,
        target_type="user",
        target_id=user.id,
        ip=ip,
    )
    return user, after


def grant_guardian_consent(db: Session, raw_token: str, ip: str | None) -> User:
    user = _consume_token(db, raw_token, TokenPurpose.GUARDIAN_CONSENT)
    profile = db.scalar(select(StudentProfile).where(StudentProfile.user_id == user.id))
    db.add(
        ConsentRecord(
            user_id=user.id,
            consent_type="guardian",
            policy_version=settings.policy_version,
            granted_by="guardian",
            guardian_email=profile.guardian_email if profile else None,
            granted=True,
            ip_address=ip,
        )
    )
    if user.status == UserStatus.PENDING_CONSENT:
        user.status = UserStatus.ACTIVE
    audit.record(
        db,
        "user.guardian_consent_granted",
        actor_user_id=None,
        target_type="user",
        target_id=user.id,
        ip=ip,
    )
    return user


def resend_guardian_consent(db: Session, email: str) -> PostCommit | None:
    user = get_active_user_by_email(db, email)
    if user is None or user.status != UserStatus.PENDING_CONSENT:
        return None
    profile = db.scalar(select(StudentProfile).where(StudentProfile.user_id == user.id))
    if not profile or not profile.guardian_email:
        return None
    token = _issue_token(db, user, TokenPurpose.GUARDIAN_CONSENT, timedelta(days=7))
    return _guardian_email(profile.guardian_email, profile.display_name, token)


# ── Login sessions ───────────────────────────────────────────────────────────


@dataclass
class IssuedSession:
    user: User
    access_token: str
    expires_in: int
    refresh_token: str
    session_id: uuid.UUID


_STATUS_ERRORS = {
    UserStatus.PENDING_VERIFICATION: ("email_not_verified", "Please verify your email first."),
    UserStatus.PENDING_CONSENT: (
        "guardian_consent_pending",
        "Waiting for your parent or guardian to give consent.",
    ),
    UserStatus.SUSPENDED: ("account_suspended", "This account has been suspended."),
}


def _issue(db: Session, user: User, family_id: uuid.UUID, ua: str | None, ip: str | None):
    raw, digest = new_opaque_token()
    sess = AuthSession(
        user_id=user.id,
        family_id=family_id,
        token_hash=digest,
        expires_at=now() + timedelta(days=settings.refresh_token_days),
        user_agent=ua,
        ip_address=ip,
    )
    db.add(sess)
    db.flush()
    access, ttl = create_access_token(user.id, sess.id, user.role_names, user.permission_codes)
    return IssuedSession(user, access, ttl, raw, sess.id)


def login(
    db: Session, email: str, password: str, portal: str, ip: str | None, ua: str | None
) -> IssuedSession:
    """`portal` is "student" or "admin"; the two portals are separate by design."""
    email = normalize_email(email)
    user = get_active_user_by_email(db, email)

    def fail(reason: str, exc: AppError) -> AppError:
        security.record_login(
            db,
            email=email,
            portal=portal,
            success=False,
            user_id=user.id if user else None,
            reason=reason,
            ip=ip,
            user_agent=ua,
        )
        return exc

    if not verify_password(password, user.password_hash if user else None) or user is None:
        raise fail(
            "bad_credentials",
            Unauthorized("Incorrect email or password.", code="invalid_credentials"),
        )
    if user.status in _STATUS_ERRORS:
        code, msg = _STATUS_ERRORS[user.status]
        raise fail(code, Forbidden(msg, code=code))
    is_admin = ADMIN_ROLE in user.role_names
    if portal == "admin" and not is_admin:
        raise fail(
            "not_admin", Forbidden("This account can't access the admin portal.", code="not_admin")
        )
    if portal == "student" and is_admin:
        raise fail(
            "use_admin_portal",
            Forbidden("Administrators sign in through the admin portal.", code="use_admin_portal"),
        )
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)

    user.last_login_at = now()
    issued = _issue(db, user, uuid.uuid4(), ua, ip)
    security.record_login(
        db, email=email, portal=portal, success=True, user_id=user.id, ip=ip, user_agent=ua
    )
    return issued


def refresh(db: Session, raw_refresh: str, ip: str | None, ua: str | None) -> IssuedSession:
    sess = db.scalar(
        select(AuthSession)
        .where(AuthSession.token_hash == hash_token(raw_refresh))
        .with_for_update()
    )
    if sess is None:
        raise Unauthorized("Session expired. Please sign in again.", code="invalid_refresh")
    if sess.revoked_at is not None:
        if sess.revoked_reason == "rotated":
            # A rotated token came back: it was stolen or replayed. Kill the whole family.
            revoke_family(db, sess.family_id, "reuse_detected")
            audit.record(
                db,
                "auth.refresh_reuse_detected",
                actor_user_id=sess.user_id,
                target_type="auth_session",
                target_id=sess.family_id,
                ip=ip,
            )
        raise Unauthorized("Session expired. Please sign in again.", code="invalid_refresh")
    if sess.expires_at < now():
        raise Unauthorized("Session expired. Please sign in again.", code="invalid_refresh")

    user = db.get(User, sess.user_id)
    if user is None or user.status != UserStatus.ACTIVE or user.deleted_at is not None:
        revoke_family(db, sess.family_id, "user_inactive")
        raise Unauthorized("Session expired. Please sign in again.", code="invalid_refresh")

    issued = _issue(db, user, sess.family_id, ua, ip)
    sess.revoked_at = now()
    sess.revoked_reason = "rotated"
    sess.replaced_by_id = issued.session_id
    sess.last_used_at = now()
    return issued


def revoke_family(db: Session, family_id: uuid.UUID, reason: str) -> None:
    db.execute(
        update(AuthSession)
        .where(AuthSession.family_id == family_id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=now(), revoked_reason=reason)
    )


def revoke_all_for_user(db: Session, user_id: uuid.UUID, reason: str) -> None:
    db.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=now(), revoked_reason=reason)
    )


def logout(db: Session, raw_refresh: str | None) -> None:
    if not raw_refresh:
        return
    sess = db.scalar(select(AuthSession).where(AuthSession.token_hash == hash_token(raw_refresh)))
    if sess:
        revoke_family(db, sess.family_id, "logout")


def active_sessions(db: Session, user_id: uuid.UUID) -> list[AuthSession]:
    return list(
        db.scalars(
            select(AuthSession)
            .where(
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > now(),
            )
            .order_by(AuthSession.created_at.desc())
        )
    )


def revoke_session(db: Session, user_id: uuid.UUID, session_id: uuid.UUID) -> None:
    sess = db.get(AuthSession, session_id)
    if sess is None or sess.user_id != user_id:  # ownership check
        raise AppError("Session not found.", code="not_found")
    revoke_family(db, sess.family_id, "user_revoked")


def is_session_live(db: Session, session_id: uuid.UUID) -> bool:
    """Is the login behind an access token still valid?

    An access token minted before a refresh carries the now-rotated session id; it stays
    valid while its family is alive. Logout, suspension or reuse detection revoke the
    family, which kills every outstanding access token immediately.
    """
    sess = db.get(AuthSession, session_id)
    if sess is None or sess.expires_at < now():
        return False
    if sess.revoked_at is None:
        return True
    if sess.revoked_reason != "rotated":
        return False
    live = db.scalar(
        select(AuthSession.id)
        .where(AuthSession.family_id == sess.family_id, AuthSession.revoked_at.is_(None))
        .limit(1)
    )
    return live is not None


# ── Passwords ────────────────────────────────────────────────────────────────


def request_password_reset(db: Session, email: str) -> PostCommit | None:
    user = get_active_user_by_email(db, email)
    if user is None or user.status in (UserStatus.SUSPENDED, UserStatus.DELETED):
        return None
    token = _issue_token(
        db, user, TokenPurpose.RESET_PASSWORD, timedelta(minutes=settings.reset_token_minutes)
    )
    link = _link("/reset-password", token)
    return lambda: send_email(
        user.email,
        "Reset your AdaptiveLearn AI password",
        f"Someone asked to reset the password for this account.\n\nReset it here:\n{link}\n\n"
        f"This link expires in {settings.reset_token_minutes} minutes. If it wasn't you, "
        f"ignore this email — your password won't change.",
    )


def reset_password(db: Session, raw_token: str, new_password: str, ip: str | None) -> None:
    user = _consume_token(db, raw_token, TokenPurpose.RESET_PASSWORD)
    user.password_hash = hash_password(new_password)
    # Clicking the emailed link proves inbox ownership.
    if user.status == UserStatus.PENDING_VERIFICATION and user.email_verified_at is None:
        user.email_verified_at = now()
    revoke_all_for_user(db, user.id, "password_reset")
    audit.record(
        db,
        "user.password_reset",
        actor_user_id=user.id,
        target_type="user",
        target_id=user.id,
        ip=ip,
    )


def change_password(
    db: Session, user: User, current: str, new: str, keep_session: uuid.UUID, ip: str | None
) -> None:
    if not verify_password(current, user.password_hash):
        raise AppError("Current password is incorrect.", code="wrong_password")
    user.password_hash = hash_password(new)
    # Sign out every other device; keep the one making the change.
    keep = db.get(AuthSession, keep_session)
    stmt = update(AuthSession).where(
        AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None)
    )
    if keep is not None:
        stmt = stmt.where(AuthSession.family_id != keep.family_id)
    db.execute(stmt.values(revoked_at=now(), revoked_reason="password_changed"))
    audit.record(
        db,
        "user.password_changed",
        actor_user_id=user.id,
        target_type="user",
        target_id=user.id,
        ip=ip,
    )


# ── Account status (used by administration) ──────────────────────────────────


def set_status(
    db: Session,
    actor: uuid.UUID,
    user: User,
    status: UserStatus,
    reason: str | None,
    ip: str | None,
) -> None:
    if user.id == actor:
        raise Forbidden("You can't change your own account status.", code="self_action")
    if status == UserStatus.SUSPENDED:
        user.status = UserStatus.SUSPENDED
        user.suspended_reason = reason
        revoke_all_for_user(db, user.id, "suspended")
        action = "user.suspended"
    elif status == UserStatus.ACTIVE:
        if user.status == UserStatus.DELETED:
            raise AppError("Deleted accounts can't be reactivated.", code="deleted")
        user.status = UserStatus.ACTIVE
        user.suspended_reason = None
        user.email_verified_at = user.email_verified_at or now()
        action = "user.activated"
    else:
        raise AppError("Unsupported status change.", code="bad_status")
    audit.record(
        db,
        action,
        actor_user_id=actor,
        target_type="user",
        target_id=user.id,
        details={"reason": reason} if reason else {},
        ip=ip,
    )


def create_super_admin(db: Session, email: str, password: str) -> User:
    email = normalize_email(email)
    if get_active_user_by_email(db, email):
        raise Conflict("An account with this email already exists.", code="email_taken")
    user = User(
        email=email,
        password_hash=hash_password(password),
        status=UserStatus.ACTIVE,
        email_verified_at=now(),
    )
    user.roles = [_role(db, ADMIN_ROLE)]
    db.add(user)
    db.flush()
    audit.record(
        db,
        "admin.created",
        actor_user_id=None,
        target_type="user",
        target_id=user.id,
        details={"via": "cli"},
    )
    return user
