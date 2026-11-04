"""/api/v1/curriculum — browse the student's curriculum with mastery and practice status."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.config.database import DbSession
from app.modules.curriculum import service
from app.modules.knowledge_model import service as knowledge
from app.modules.question_bank import service as qbank
from app.modules.users.service import GOALS, require_profile
from app.shared.exceptions import AppError
from app.shared.permissions import CurrentStudent

router = APIRouter(prefix="/curriculum", tags=["curriculum"])


@router.get("/options")
def options(_: CurrentStudent, db: DbSession):
    """Boards/exams with their published curricula, plus learning goals — for onboarding."""
    return {
        "boards": service.onboarding_options(db),
        "goals": [{"id": k, "label": v} for k, v in GOALS.items()],
    }


def _my_curriculum(db, p):
    profile = require_profile(db, p.user_id)
    if not profile.curriculum_id:
        raise AppError("Set up your curriculum first.", code="not_onboarded")
    return profile


@router.get("/mine")
def my_curriculum(p: CurrentStudent, db: DbSession):
    profile = _my_curriculum(db, p)
    subject_ids = (profile.preferences or {}).get("subject_ids") or None
    tree = service.tree(db, profile.curriculum_id, subject_ids=subject_ids)
    ids = [
        c["id"]
        for s in tree["subjects"]
        for ch in s["chapters"]
        for t in ch["topics"]
        for c in t["concepts"]
    ]
    mastery = knowledge.mastery_map(db, p.user_id, ids)
    counts = qbank.published_counts(db, ids)
    for s in tree["subjects"]:
        for ch in s["chapters"]:
            levels = []
            for t in ch["topics"]:
                for c in t["concepts"]:
                    c.update(knowledge.describe(mastery.get(c["id"])))
                    c["question_count"] = counts.get(c["id"], 0)
                    levels.append(c["level"])
            total = len(levels)
            ch["concept_count"] = total
            ch["completed_count"] = sum(lv in ("proficient", "mastered") for lv in levels)
            ch["practisable"] = any(
                counts.get(c["id"]) for t in ch["topics"] for c in t["concepts"]
            )
    return tree


@router.get("/search")
def search(p: CurrentStudent, db: DbSession, q: Annotated[str, Query(min_length=2, max_length=80)]):
    profile = _my_curriculum(db, p)
    return service.search_concepts(db, profile.curriculum_id, q)


@router.get("/concepts/{concept_id}")
def concept(concept_id: int, p: CurrentStudent, db: DbSession):
    d = service.concept_detail(db, concept_id)
    ids = [d["id"]] + [x["id"] for x in d["prerequisites"]] + [x["id"] for x in d["unlocks"]]
    mastery = knowledge.mastery_map(db, p.user_id, ids)
    d.update(knowledge.describe(mastery.get(d["id"])))
    for x in d["prerequisites"] + d["unlocks"]:
        x.update(knowledge.describe(mastery.get(x["id"])))
    d["question_count"] = qbank.published_counts(db, [d["id"]]).get(d["id"], 0)
    return d
