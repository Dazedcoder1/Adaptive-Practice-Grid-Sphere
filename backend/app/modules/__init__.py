"""Domain modules. Each owns its models, schemas, service and router."""

from fastapi import APIRouter

from app.modules.academic.router import router as academic
from app.modules.adaptive.router import router as adaptive
from app.modules.administration.router import router as administration
from app.modules.ai_tutor.router import router as ai_tutor
from app.modules.analytics.router import router as analytics
from app.modules.assessment.router import router as assessment
from app.modules.audit.router import router as audit
from app.modules.curriculum.router import router as curriculum
from app.modules.error_notebook.router import router as error_notebook
from app.modules.gamification.router import router as gamification
from app.modules.identity.router import router as identity
from app.modules.knowledge_model.router import router as knowledge_model
from app.modules.learning_content.router import router as learning_content
from app.modules.notifications.router import router as notifications
from app.modules.practice.router import router as practice
from app.modules.question_bank.router import router as question_bank
from app.modules.rag.router import router as rag
from app.modules.revision.router import router as revision
from app.modules.security.router import router as security
from app.modules.users.router import router as users

api_router = APIRouter()
for r in (
    academic,
    adaptive,
    administration,
    ai_tutor,
    analytics,
    assessment,
    audit,
    curriculum,
    error_notebook,
    gamification,
    identity,
    knowledge_model,
    learning_content,
    notifications,
    practice,
    question_bank,
    rag,
    revision,
    security,
    users,
):
    api_router.include_router(r)
