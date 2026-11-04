"""AI settings, usage recording and budget checks — shared by the tutor and RAG ingestion.

Days are counted in India Standard Time, so "today's" limits reset at midnight IST.
"""

import uuid
from datetime import datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.modules.ai_tutor.models import AiSettings, AiUsage, TutorConversation, TutorMessage

PLATFORM_TZ = ZoneInfo("Asia/Kolkata")
_MTOK = Decimal(1_000_000)


def get_settings(db: Session) -> AiSettings:
    row = db.get(AiSettings, 1)
    if row is None:
        db.execute(insert(AiSettings).values(id=1).on_conflict_do_nothing())
        db.flush()
        row = db.get(AiSettings, 1)
    return row


def day_start(now: datetime | None = None) -> datetime:
    local = (now or datetime.now(PLATFORM_TZ)).astimezone(PLATFORM_TZ)
    return datetime.combine(local.date(), time.min, PLATFORM_TZ)


def cost_of(s: AiSettings, feature: str, input_tokens: int, output_tokens: int) -> Decimal:
    if feature == "embedding":
        return Decimal(input_tokens) * s.embedding_price_per_mtok / _MTOK
    return (
        Decimal(input_tokens) * s.input_price_per_mtok
        + Decimal(output_tokens) * s.output_price_per_mtok
    ) / _MTOK


def record_usage(
    db: Session,
    *,
    feature: str,
    provider: str,
    model: str,
    user_id: uuid.UUID | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    latency_ms: int = 0,
    ok: bool = True,
    error_code: str | None = None,
    fallback_used: bool = False,
) -> AiUsage:
    s = get_settings(db)
    row = AiUsage(
        feature=feature,
        user_id=user_id,
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_of(s, feature, input_tokens, output_tokens) if ok else Decimal(0),
        latency_ms=latency_ms,
        ok=ok,
        error_code=error_code,
        fallback_used=fallback_used,
    )
    db.add(row)
    db.flush()
    return row


def cost_today(db: Session) -> Decimal:
    return db.scalar(
        select(func.coalesce(func.sum(AiUsage.cost_usd), 0)).where(
            AiUsage.created_at >= day_start()
        )
    ) or Decimal(0)


def tokens_today(db: Session, user_id: uuid.UUID) -> int:
    return int(
        db.scalar(
            select(func.coalesce(func.sum(AiUsage.input_tokens + AiUsage.output_tokens), 0)).where(
                AiUsage.user_id == user_id, AiUsage.created_at >= day_start()
            )
        )
        or 0
    )


def ai_messages_today(db: Session, user_id: uuid.UUID) -> int:
    """Tutor replies produced by the AI today (notes-mode replies don't count)."""
    return int(
        db.scalar(
            select(func.count())
            .select_from(TutorMessage)
            .join(TutorConversation, TutorConversation.id == TutorMessage.conversation_id)
            .where(
                TutorConversation.student_id == user_id,
                TutorMessage.role == "tutor",
                TutorMessage.source == "ai",
                TutorMessage.created_at >= day_start(),
            )
        )
        or 0
    )


def since(days: int) -> datetime:
    return day_start() - timedelta(days=days - 1)
