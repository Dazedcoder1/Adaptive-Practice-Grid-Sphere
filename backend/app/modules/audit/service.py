"""Write-only API for the audit log. Callers add a row inside their own transaction, so
the audit entry commits (or rolls back) together with the action it describes."""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.modules.audit.models import AuditLog


def record(
    db: Session,
    action: str,
    *,
    actor_user_id: uuid.UUID | None,
    target_type: str | None = None,
    target_id: str | uuid.UUID | None = None,
    details: dict[str, Any] | None = None,
    ip: str | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else None,
            details=details or {},
            ip_address=ip,
        )
    )
