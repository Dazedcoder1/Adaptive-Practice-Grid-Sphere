"""/api/v1/auth — registration, verification, login (student + admin), sessions, passwords."""

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Cookie, Request, Response, status

from app.config.database import DbSession, transaction
from app.config.settings import settings
from app.modules.identity import service
from app.modules.identity.models import AuthSession, User
from app.modules.identity.schemas import (
    AuthUser,
    ChangePasswordRequest,
    EmailRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
    SessionOut,
    TokenRequest,
    TokenResponse,
)
from app.modules.security.service import rate_limit
from app.modules.users import service as users
from app.shared.exceptions import AppError, Unauthorized
from app.shared.permissions import CurrentUser
from app.shared.request import client_ip, require_trusted_origin, user_agent

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_PATH = f"{settings.api_v1_prefix}/auth"
RefreshCookie = Annotated[str | None, Cookie(alias=settings.refresh_cookie_name)]

GENERIC_EMAIL_MSG = "If an account matches, we've sent an email with next steps."


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        settings.refresh_cookie_name,
        token,
        max_age=settings.refresh_token_days * 86400,
        httponly=True,  # not readable by JavaScript (XSS can't steal it)
        secure=settings.is_production,
        samesite="lax",
        path=COOKIE_PATH,  # only sent to /auth endpoints
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(settings.refresh_cookie_name, path=COOKIE_PATH)


def auth_user(db, user: User) -> AuthUser:
    profile = users.get_profile(db, user.id)
    return AuthUser(
        id=user.id,
        email=user.email,
        status=user.status.value,
        roles=user.role_names,
        permissions=user.permission_codes,
        display_name=profile.display_name if profile else None,
        onboarding_completed=profile.onboarding_completed if profile else None,
    )


def _token_response(db, response: Response, issued: service.IssuedSession) -> TokenResponse:
    _set_refresh_cookie(response, issued.refresh_token)
    return TokenResponse(
        access_token=issued.access_token,
        expires_in=issued.expires_in,
        user=auth_user(db, issued.user),
    )


# ── Registration & activation ────────────────────────────────────────────────


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=RegisterResponse)
def register(body: RegisterRequest, request: Request, db: DbSession, bg: BackgroundTasks):
    ip = client_ip(request)
    rate_limit(f"register:{ip}", settings.rate_limit_register)
    with transaction(db):
        user, send = service.register_student(
            db,
            service.RegisterInput(
                email=str(body.email),
                password=body.password,
                display_name=body.display_name,
                is_minor=body.is_minor,
                guardian_email=str(body.guardian_email) if body.guardian_email else None,
                accepted_terms=body.accept_terms,
            ),
            ip,
        )
    bg.add_task(send)
    return RegisterResponse(
        user_id=user.id,
        status=user.status.value,
        message="Account created. Check your email to verify your address.",
    )


@router.post("/verify-email", response_model=MessageResponse)
def verify_email(body: TokenRequest, request: Request, db: DbSession, bg: BackgroundTasks):
    with transaction(db):
        user, send = service.verify_email(db, body.token, client_ip(request))
        status_ = user.status
    if send:
        bg.add_task(send)
        return MessageResponse(
            message="Email verified. We've asked your parent or guardian for consent — you can "
            "sign in once they approve."
        )
    return MessageResponse(message=f"Email verified. Account status: {status_.value}.")


@router.post("/resend-verification", status_code=202, response_model=MessageResponse)
def resend_verification(body: EmailRequest, db: DbSession, bg: BackgroundTasks):
    rate_limit(f"email:{body.email}", settings.rate_limit_email)
    with transaction(db):
        send = service.resend_verification(db, str(body.email))
    if send:
        bg.add_task(send)
    return MessageResponse(message=GENERIC_EMAIL_MSG)


@router.post("/guardian-consent", response_model=MessageResponse)
def guardian_consent(body: TokenRequest, request: Request, db: DbSession):
    with transaction(db):
        service.grant_guardian_consent(db, body.token, client_ip(request))
    return MessageResponse(message="Thank you. Consent recorded and the account is now active.")


@router.post("/resend-guardian-consent", status_code=202, response_model=MessageResponse)
def resend_guardian_consent(body: EmailRequest, db: DbSession, bg: BackgroundTasks):
    rate_limit(f"email:{body.email}", settings.rate_limit_email)
    with transaction(db):
        send = service.resend_guardian_consent(db, str(body.email))
    if send:
        bg.add_task(send)
    return MessageResponse(message=GENERIC_EMAIL_MSG)


# ── Login / refresh / logout ─────────────────────────────────────────────────


def _login(
    portal: str, body: LoginRequest, request: Request, response: Response, db
) -> TokenResponse:
    ip = client_ip(request)
    rate_limit(f"login:{portal}:{ip}:{body.email}", settings.rate_limit_login)
    # Failed attempts must still persist their login_event, so commit on error too.
    try:
        issued = service.login(db, str(body.email), body.password, portal, ip, user_agent(request))
        result = _token_response(db, response, issued)
        db.commit()
        return result
    except AppError:
        db.commit()  # persist the failed-login event
        raise


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, response: Response, db: DbSession):
    """Student portal sign-in."""
    return _login("student", body, request, response, db)


@router.post("/admin/login", response_model=TokenResponse)
def admin_login(body: LoginRequest, request: Request, response: Response, db: DbSession):
    """Super Admin portal sign-in."""
    return _login("admin", body, request, response, db)


@router.post("/refresh", response_model=TokenResponse)
def refresh(request: Request, response: Response, db: DbSession, token: RefreshCookie = None):
    require_trusted_origin(request)
    if not token:
        raise Unauthorized("Not signed in.", code="invalid_refresh")
    try:
        issued = service.refresh(db, token, client_ip(request), user_agent(request))
        result = _token_response(db, response, issued)
        db.commit()
        return result
    except AppError:
        db.commit()  # keep reuse-detection revocations even though we return 401
        _clear_refresh_cookie(response)
        raise


@router.post("/logout", response_model=MessageResponse)
def logout(request: Request, response: Response, db: DbSession, token: RefreshCookie = None):
    require_trusted_origin(request)
    with transaction(db):
        service.logout(db, token)
    _clear_refresh_cookie(response)
    return MessageResponse(message="Signed out.")


@router.get("/me", response_model=AuthUser)
def me(p: CurrentUser, db: DbSession):
    return auth_user(db, db.get(User, p.user_id))


# ── Session management ───────────────────────────────────────────────────────


@router.get("/sessions", response_model=list[SessionOut])
def sessions(p: CurrentUser, db: DbSession):
    current = db.get(AuthSession, p.session_id)
    out = []
    for s in service.active_sessions(db, p.user_id):
        item = SessionOut.model_validate(s)
        item.current = current is not None and s.family_id == current.family_id
        out.append(item)
    return out


@router.delete("/sessions/{session_id}", response_model=MessageResponse)
def revoke_session(session_id: uuid.UUID, p: CurrentUser, db: DbSession):
    with transaction(db):
        service.revoke_session(db, p.user_id, session_id)
    return MessageResponse(message="Session signed out.")


@router.post("/logout-all", response_model=MessageResponse)
def logout_all(p: CurrentUser, response: Response, db: DbSession):
    with transaction(db):
        service.revoke_all_for_user(db, p.user_id, "logout_all")
    _clear_refresh_cookie(response)
    return MessageResponse(message="Signed out of all devices.")


# ── Passwords ────────────────────────────────────────────────────────────────


@router.post("/forgot-password", status_code=202, response_model=MessageResponse)
def forgot_password(body: EmailRequest, db: DbSession, bg: BackgroundTasks):
    rate_limit(f"email:{body.email}", settings.rate_limit_email)
    with transaction(db):
        send = service.request_password_reset(db, str(body.email))
    if send:
        bg.add_task(send)
    return MessageResponse(message=GENERIC_EMAIL_MSG)


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(body: ResetPasswordRequest, request: Request, db: DbSession):
    with transaction(db):
        service.reset_password(db, body.token, body.new_password, client_ip(request))
    return MessageResponse(message="Password updated. Please sign in with your new password.")


@router.post("/change-password", response_model=MessageResponse)
def change_password(body: ChangePasswordRequest, request: Request, p: CurrentUser, db: DbSession):
    with transaction(db):
        service.change_password(
            db,
            db.get(User, p.user_id),
            body.current_password,
            body.new_password,
            p.session_id,
            client_ip(request),
        )
    return MessageResponse(message="Password changed. Other devices have been signed out.")
