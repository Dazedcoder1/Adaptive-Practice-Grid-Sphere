"""/api/v1/ai/tutor — the student's AI tutor (design §9 AI APIs)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.config.database import DbSession, transaction
from app.modules.ai_tutor import service
from app.modules.ai_tutor.schemas import ChatIn, FeedbackIn, QuestionHelpIn
from app.modules.security.service import rate_limit
from app.shared.permissions import CurrentStudent

router = APIRouter(prefix="/ai/tutor", tags=["ai tutor"])
TUTOR_RATE = "12/60"


def _ask(db, p, a: service.Ask):
    rate_limit(f"tutor:{p.user_id}", TUTOR_RATE)
    with transaction(db):
        return service.ask(db, p.user_id, a)


@router.get("/status")
def tutor_status(p: CurrentStudent, db: DbSession):
    with transaction(db):
        return service.status(db, p.user_id)


@router.post("/chat")
def chat(body: ChatIn, p: CurrentStudent, db: DbSession):
    """Send a message to the tutor in one of the five modes."""
    return _ask(db, p, service.Ask(**body.model_dump()))


@router.post("/hint")
def hint(body: QuestionHelpIn, p: CurrentStudent, db: DbSession):
    """A hint for a practice question the student is working on. Counts like a hint."""
    return _ask(
        db,
        p,
        service.Ask(
            mode="hint",
            message="Can I have a hint for this question?",
            conversation_id=body.conversation_id,
            session_question_id=body.session_question_id,
        ),
    )


@router.post("/explain")
def explain(body: QuestionHelpIn, p: CurrentStudent, db: DbSession):
    """Explain an answered practice question — what went wrong, or why the answer is right."""
    return _ask(
        db,
        p,
        service.Ask(
            mode="mistake",
            message="Can you explain this question and where I went wrong, if I did?",
            conversation_id=body.conversation_id,
            session_question_id=body.session_question_id,
        ),
    )


@router.get("/conversations")
def conversations(
    p: CurrentStudent, db: DbSession, limit: Annotated[int, Query(ge=1, le=100)] = 30
):
    return service.list_conversations(db, p.user_id, limit)


@router.get("/conversations/{conv_id}")
def conversation(conv_id: uuid.UUID, p: CurrentStudent, db: DbSession):
    return service.get_conversation(db, p.user_id, conv_id)


@router.delete("/conversations/{conv_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conv_id: uuid.UUID, p: CurrentStudent, db: DbSession):
    with transaction(db):
        service.delete_conversation(db, p.user_id, conv_id)


@router.post("/messages/{message_id}/feedback")
def feedback(message_id: uuid.UUID, body: FeedbackIn, p: CurrentStudent, db: DbSession):
    with transaction(db):
        return service.rate(db, p.user_id, message_id, body.helpful)
