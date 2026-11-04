"""/api/v1/adaptive — the student's knowledge profile, weak concepts and recommendations."""

from fastapi import APIRouter

from app.config.database import DbSession
from app.modules.adaptive import service
from app.modules.curriculum import service as curriculum
from app.modules.knowledge_model import bkt
from app.modules.knowledge_model import service as knowledge
from app.shared.permissions import CurrentStudent

router = APIRouter(prefix="/adaptive", tags=["adaptive"])


@router.get("/mastery")
def mastery(p: CurrentStudent, db: DbSession):
    rows = knowledge.mastery_map(db, p.user_id)
    ctx = curriculum.concept_context(db, list(rows))
    return {
        "model_version": bkt.MODEL_VERSION,
        "note": "Mastery is an estimate from your answers, not a calibrated probability.",
        "concepts": sorted(
            [{**ctx.get(cid, {"id": cid}), **knowledge.describe(m)} for cid, m in rows.items()],
            key=lambda x: x["p_known"],
        ),
    }


@router.get("/weak-concepts")
def weak(p: CurrentStudent, db: DbSession):
    return service.weak_concepts(db, p.user_id)


@router.get("/recommendations")
def recommendations(p: CurrentStudent, db: DbSession):
    return service.recommendations(db, p.user_id)
