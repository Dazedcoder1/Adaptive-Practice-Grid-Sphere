"""/api/v1/revision — the student's spaced-repetition queue."""

from fastapi import APIRouter

from app.config.database import DbSession
from app.modules.revision import service
from app.shared.permissions import CurrentStudent

router = APIRouter(prefix="/revision", tags=["revision"])


@router.get("/queue")
def queue(p: CurrentStudent, db: DbSession):
    return service.enriched_queue(db, p.user_id, horizon_days=14)
