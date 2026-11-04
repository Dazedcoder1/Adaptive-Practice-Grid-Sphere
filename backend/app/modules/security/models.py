"""Login activity for monitoring failed logins and suspicious access."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class LoginEvent(Base):
    __tablename__ = "login_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    portal: Mapped[str] = mapped_column(String(16), nullable=False)  # student | admin
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(64))
    ip_address: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_login_events_created", "created_at"),
        Index("ix_login_events_user_created", "user_id", "created_at"),
        Index("ix_login_events_failed", "success", "created_at"),
    )
