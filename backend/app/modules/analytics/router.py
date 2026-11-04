"""/api/v1/analytics — the student's dashboard figures (all from real records)."""

from fastapi import APIRouter

from app.config.database import DbSession
from app.modules.analytics import service
from app.shared.permissions import CurrentStudent

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard")
def dashboard(p: CurrentStudent, db: DbSession):
    return service.dashboard(db, p.user_id)
