"""Auth dependencies: who is calling and what they may do (RBAC + object ownership).

The access token is a short-lived JWT, but every request also checks the user and the
login session in the database, so suspension and logout take effect immediately.
"""

import uuid
from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config.database import DbSession
from app.config.security import decode_access_token
from app.shared.exceptions import Forbidden, Unauthorized

_bearer = HTTPBearer(auto_error=False)

STUDENT = "student"
SUPER_ADMIN = "super_admin"


@dataclass(frozen=True)
class Principal:
    user_id: uuid.UUID
    session_id: uuid.UUID
    roles: frozenset[str]
    permissions: frozenset[str]

    @property
    def is_admin(self) -> bool:
        return SUPER_ADMIN in self.roles


def current_principal(
    db: DbSession,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Principal:
    # Imported here: identity depends on shared, not the other way round at import time.
    from app.modules.identity.models import User, UserStatus
    from app.modules.identity.service import is_session_live

    if creds is None:
        raise Unauthorized("Not signed in.", code="not_authenticated")
    try:
        payload = decode_access_token(creds.credentials)
        user_id, session_id = uuid.UUID(payload["sub"]), uuid.UUID(payload["sid"])
    except (jwt.PyJWTError, ValueError, KeyError) as e:
        raise Unauthorized("Session expired.", code="token_invalid") from e

    user = db.get(User, user_id)
    if user is None or user.status != UserStatus.ACTIVE or user.deleted_at is not None:
        raise Unauthorized("Session expired.", code="token_invalid")
    if not is_session_live(db, session_id):
        raise Unauthorized("Session expired.", code="token_invalid")

    return Principal(
        user_id=user.id,
        session_id=session_id,
        roles=frozenset(user.role_names),
        permissions=frozenset(user.permission_codes),
    )


CurrentUser = Annotated[Principal, Depends(current_principal)]


def require_student(p: CurrentUser) -> Principal:
    if STUDENT not in p.roles:
        raise Forbidden("Student account required.", code="student_only")
    return p


def require_admin(p: CurrentUser) -> Principal:
    if not p.is_admin:
        raise Forbidden("Administrator access required.", code="admin_only")
    return p


CurrentStudent = Annotated[Principal, Depends(require_student)]
CurrentAdmin = Annotated[Principal, Depends(require_admin)]


def require_permission(code: str):
    def _check(p: CurrentAdmin) -> Principal:
        if code not in p.permissions:
            raise Forbidden("You don't have permission to do that.", code="missing_permission")
        return p

    return _check


def ensure_owner(p: Principal, owner_user_id: uuid.UUID) -> None:
    """Object-level authorisation: call on every student-owned resource."""
    if p.user_id != owner_user_id and not p.is_admin:
        raise Forbidden("Not found.", code="not_owner")
