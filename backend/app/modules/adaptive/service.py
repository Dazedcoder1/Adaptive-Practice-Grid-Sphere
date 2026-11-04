"""Recommendation engine: the next best activity for a student, with a stated reason."""

import uuid

from sqlalchemy.orm import Session

from app.modules.curriculum import service as curriculum
from app.modules.knowledge_model import bkt
from app.modules.knowledge_model import service as knowledge
from app.modules.question_bank import service as qbank
from app.modules.revision import service as revision


def _scope(db: Session, profile) -> list[int]:
    if profile is None or profile.curriculum_id is None:
        return []
    subject_ids = (profile.preferences or {}).get("subject_ids") or []
    ids: list[int] = []
    for sid in subject_ids:
        ids += curriculum.concept_ids_for(db, subject_id=sid)
    return ids or curriculum.concept_ids_for(db, curriculum_id=profile.curriculum_id)


def recommendations(db: Session, student_id: uuid.UUID, limit: int = 4) -> list[dict]:
    from app.modules.practice import service as practice
    from app.modules.users.service import get_profile

    profile = get_profile(db, student_id)
    recs: list[dict] = []

    open_sessions = practice.list_sessions(db, student_id, status="open", limit=1)
    if open_sessions:
        s = open_sessions[0]
        recs.append(
            {
                "type": "continue_session",
                "title": f"Continue: {s['title']}",
                "reason": f"You've answered {s['answered_count']} of {s['target_count']}.",
                "session_id": s["id"],
            }
        )

    concepts = _scope(db, profile)
    if not concepts:
        if profile and not profile.onboarding_completed:
            recs.append(
                {
                    "type": "onboarding",
                    "title": "Set up your learning path",
                    "reason": "Choose your curriculum and subjects to get started.",
                }
            )
        return recs[:limit]

    available = qbank.published_counts(db, concepts)
    practisable = [c for c in concepts if available.get(c)]
    mastery = knowledge.mastery_map(db, student_id, concepts)
    ctx = curriculum.concept_context(db, concepts)
    prereqs = curriculum.prerequisites_map(db, concepts)

    if not mastery and practisable:
        first = ctx[practisable[0]]
        recs.append(
            {
                "type": "diagnostic",
                "title": f"Diagnostic: {first['chapter']['name']}",
                "reason": "A short diagnostic finds your starting point so practice "
                "can adapt to you.",
                "chapter_id": first["chapter"]["id"],
            }
        )

    due = revision.due_concept_ids(db, student_id)
    if due:
        recs.append(
            {
                "type": "revision",
                "title": f"Revise {len(due)} concept(s)",
                "reason": "These are due for review, based on when you last got them "
                "right or wrong.",
            }
        )

    practised = [c for c in practisable if c in mastery]
    weak = sorted(
        (
            c
            for c in practised
            if bkt.level(mastery[c].p_known, mastery[c].attempts) in ("weak", "developing")
        ),
        key=lambda c: mastery[c].p_known,
    )
    for c in weak[:2]:
        gap = [
            p
            for p in prereqs.get(c, [])
            if p in mastery and mastery[p].p_known < 0.45 and available.get(p)
        ]
        if gap:
            p = gap[0]
            recs.append(
                {
                    "type": "practice_concept",
                    "concept_id": p,
                    "title": f"Strengthen {ctx[p]['name']}",
                    "reason": f"It's a prerequisite for {ctx[c]['name']}, and your mastery "
                    f"estimate is {round(mastery[p].p_known * 100)}%.",
                }
            )
        else:
            recs.append(
                {
                    "type": "practice_concept",
                    "concept_id": c,
                    "title": f"Practise {ctx[c]['name']}",
                    "reason": f"Your mastery estimate is {round(mastery[c].p_known * 100)}%.",
                }
            )

    ready = [
        c
        for c in practisable
        if c not in mastery
        and all(p in mastery and mastery[p].p_known >= 0.6 for p in prereqs.get(c, []))
    ]
    if ready:
        c = ready[0]
        recs.append(
            {
                "type": "practice_concept",
                "concept_id": c,
                "title": f"Start {ctx[c]['name']}",
                "reason": "Next in your curriculum, and you're ready for it."
                if prereqs.get(c)
                else "Next in your curriculum.",
            }
        )

    seen, unique = set(), []
    for r in recs:
        key = (r["type"], r.get("concept_id"), r.get("session_id"))
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique[:limit]


def weak_concepts(db: Session, student_id: uuid.UUID) -> list[dict]:
    from app.modules.users.service import get_profile

    concepts = _scope(db, get_profile(db, student_id))
    mastery = knowledge.mastery_map(db, student_id, concepts or None)
    ids = [
        c for c, m in mastery.items() if bkt.level(m.p_known, m.attempts) in ("weak", "developing")
    ]
    ctx = curriculum.concept_context(db, ids)
    prereqs = curriculum.prerequisites_map(db, ids)
    out = []
    for c in sorted(ids, key=lambda c: mastery[c].p_known):
        gaps = [p for p in prereqs.get(c, []) if p in mastery and mastery[p].p_known < 0.45]
        out.append(
            {
                **ctx.get(c, {"id": c}),
                **knowledge.describe(mastery[c]),
                "weak_prerequisites": [ctx.get(p, {"id": p}) for p in gaps],
            }
        )
    if out:
        names = curriculum.concept_context(
            db, [g["id"] for o in out for g in o["weak_prerequisites"]]
        )
        for o in out:
            o["weak_prerequisites"] = [names.get(g["id"], g) for g in o["weak_prerequisites"]]
    return out
