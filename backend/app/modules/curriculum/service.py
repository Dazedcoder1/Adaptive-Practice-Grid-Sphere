"""Curriculum queries (students) and management (Super Admin)."""

from collections import defaultdict

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.curriculum.models import (
    Board,
    Chapter,
    Concept,
    ConceptPrerequisite,
    ContentStatus,
    Curriculum,
    Grade,
    Subject,
    Topic,
)
from app.shared.exceptions import AppError, Conflict, NotFound

# ── lookups shared with other modules ────────────────────────────────────────


def get_or_404(db: Session, model, obj_id):
    obj = db.get(model, obj_id)
    if obj is None:
        raise NotFound(f"{model.__name__} not found.")
    return obj


def curriculum_label(c: Curriculum) -> str:
    return c.name


def concept_ids_for(
    db: Session, *, curriculum_id=None, subject_id=None, chapter_id=None, topic_id=None
) -> list[int]:
    """Concept ids in curriculum order for a scope (most specific scope wins)."""
    stmt = (
        select(Concept.id)
        .join(Topic, Topic.id == Concept.topic_id)
        .join(Chapter, Chapter.id == Topic.chapter_id)
        .join(Subject, Subject.id == Chapter.subject_id)
    )
    if topic_id is not None:
        stmt = stmt.where(Topic.id == topic_id)
    elif chapter_id is not None:
        stmt = stmt.where(Chapter.id == chapter_id)
    elif subject_id is not None:
        stmt = stmt.where(Subject.id == subject_id)
    elif curriculum_id is not None:
        stmt = stmt.where(Subject.curriculum_id == curriculum_id)
    else:
        return []
    stmt = stmt.order_by(
        Subject.sequence, Chapter.sequence, Topic.sequence, Concept.sequence, Concept.id
    )
    return list(db.scalars(stmt))


def concept_context(db: Session, concept_ids) -> dict[int, dict]:
    """Names and breadcrumbs for a set of concepts."""
    if not concept_ids:
        return {}
    rows = db.execute(
        select(Concept, Topic, Chapter, Subject, Curriculum)
        .join(Topic, Topic.id == Concept.topic_id)
        .join(Chapter, Chapter.id == Topic.chapter_id)
        .join(Subject, Subject.id == Chapter.subject_id)
        .join(Curriculum, Curriculum.id == Subject.curriculum_id)
        .where(Concept.id.in_(list(concept_ids)))
    ).all()
    return {
        c.id: {
            "id": c.id,
            "code": c.code,
            "name": c.name,
            "topic": {"id": t.id, "name": t.name},
            "chapter": {"id": ch.id, "name": ch.name},
            "subject": {"id": s.id, "name": s.name},
            "curriculum_id": cu.id,
        }
        for c, t, ch, s, cu in rows
    }


def prerequisites_map(db: Session, concept_ids=None) -> dict[int, list[int]]:
    stmt = select(ConceptPrerequisite)
    if concept_ids is not None:
        stmt = stmt.where(ConceptPrerequisite.concept_id.in_(list(concept_ids)))
    out: dict[int, list[int]] = defaultdict(list)
    for p in db.scalars(stmt):
        out[p.concept_id].append(p.prerequisite_id)
    return dict(out)


def curriculum_of_concepts(db: Session, concept_ids) -> set[int]:
    return {v["curriculum_id"] for v in concept_context(db, concept_ids).values()}


# ── student-facing ───────────────────────────────────────────────────────────


def onboarding_options(db: Session) -> list[dict]:
    rows = db.execute(
        select(Curriculum, func.count(Subject.id))
        .outerjoin(Subject, Subject.curriculum_id == Curriculum.id)
        .where(Curriculum.status == ContentStatus.PUBLISHED)
        .group_by(Curriculum.id)
        .order_by(Curriculum.name)
    ).all()
    subjects = defaultdict(list)
    for s in db.scalars(select(Subject).order_by(Subject.sequence, Subject.name)):
        subjects[s.curriculum_id].append({"id": s.id, "name": s.name, "code": s.code})
    out = []
    for b in db.scalars(select(Board).order_by(Board.name)):
        out.append(
            {
                "id": b.id,
                "code": b.code,
                "name": b.name,
                "kind": b.kind.value,
                "study_mode": b.study_mode.value,
                "curricula": [
                    {
                        "id": c.id,
                        "name": c.name,
                        "version": c.version,
                        "is_sample": c.is_sample,
                        "grade": c.grade.name if c.grade else None,
                        "subjects": subjects[c.id],
                    }
                    for c, _ in rows
                    if c.board_id == b.id
                ],
            }
        )
    return out


def tree(db: Session, curriculum_id: int, *, subject_ids=None, include_drafts=False) -> dict:
    cur = get_or_404(db, Curriculum, curriculum_id)
    if cur.status != ContentStatus.PUBLISHED and not include_drafts:
        raise NotFound("Curriculum not found.")
    subj_stmt = select(Subject).where(Subject.curriculum_id == cur.id)
    if subject_ids:
        subj_stmt = subj_stmt.where(Subject.id.in_(subject_ids))
    subjects = list(db.scalars(subj_stmt.order_by(Subject.sequence, Subject.id)))
    sids = [s.id for s in subjects]
    chapters = (
        list(
            db.scalars(
                select(Chapter)
                .where(Chapter.subject_id.in_(sids))
                .order_by(Chapter.sequence, Chapter.id)
            )
        )
        if sids
        else []
    )
    chids = [c.id for c in chapters]
    topics = (
        list(
            db.scalars(
                select(Topic).where(Topic.chapter_id.in_(chids)).order_by(Topic.sequence, Topic.id)
            )
        )
        if chids
        else []
    )
    tids = [t.id for t in topics]
    concepts = (
        list(
            db.scalars(
                select(Concept)
                .where(Concept.topic_id.in_(tids))
                .order_by(Concept.sequence, Concept.id)
            )
        )
        if tids
        else []
    )
    prereqs = prerequisites_map(db, [c.id for c in concepts])

    by_topic = defaultdict(list)
    for c in concepts:
        by_topic[c.topic_id].append(
            {
                "id": c.id,
                "code": c.code,
                "name": c.name,
                "sequence": c.sequence,
                "prerequisite_ids": prereqs.get(c.id, []),
            }
        )
    by_chapter = defaultdict(list)
    for t in topics:
        by_chapter[t.chapter_id].append(
            {"id": t.id, "name": t.name, "sequence": t.sequence, "concepts": by_topic[t.id]}
        )
    by_subject = defaultdict(list)
    for ch in chapters:
        by_subject[ch.subject_id].append(
            {"id": ch.id, "name": ch.name, "sequence": ch.sequence, "topics": by_chapter[ch.id]}
        )
    return {
        "id": cur.id,
        "name": cur.name,
        "version": cur.version,
        "status": cur.status.value,
        "is_sample": cur.is_sample,
        "board": {"id": cur.board.id, "name": cur.board.name, "code": cur.board.code},
        "grade": {"id": cur.grade.id, "name": cur.grade.name} if cur.grade else None,
        "subjects": [
            {
                "id": s.id,
                "code": s.code,
                "name": s.name,
                "sequence": s.sequence,
                "chapters": by_subject[s.id],
            }
            for s in subjects
        ],
    }


def search_concepts(db: Session, curriculum_id: int, q: str, limit: int = 20) -> list[dict]:
    like = f"%{q.strip()}%"
    ids = list(
        db.scalars(
            select(Concept.id)
            .join(Topic, Topic.id == Concept.topic_id)
            .join(Chapter, Chapter.id == Topic.chapter_id)
            .join(Subject, Subject.id == Chapter.subject_id)
            .where(
                Subject.curriculum_id == curriculum_id,
                or_(
                    Concept.name.ilike(like),
                    Concept.description.ilike(like),
                    Topic.name.ilike(like),
                    Chapter.name.ilike(like),
                ),
            )
            .order_by(Concept.name)
            .limit(limit)
        )
    )
    ctx = concept_context(db, ids)
    return [ctx[i] for i in ids if i in ctx]


def concept_detail(db: Session, concept_id: int) -> dict:
    c = get_or_404(db, Concept, concept_id)
    ctx = concept_context(db, [c.id])[c.id]
    pre_ids = prerequisites_map(db, [c.id]).get(c.id, [])
    dependents = list(
        db.scalars(
            select(ConceptPrerequisite.concept_id).where(
                ConceptPrerequisite.prerequisite_id == c.id
            )
        )
    )
    names = concept_context(db, pre_ids + dependents)
    return {
        **ctx,
        "description": c.description,
        "prerequisites": [names[i] for i in pre_ids if i in names],
        "unlocks": [names[i] for i in dependents if i in names],
    }


# ── admin: create / update / delete ──────────────────────────────────────────


def _has_activity(db: Session, concept_ids: list[int]) -> bool:
    from app.modules.knowledge_model.models import StudentMastery
    from app.modules.question_bank.models import QuestionConcept

    if not concept_ids:
        return False
    q = db.scalar(
        select(func.count())
        .select_from(QuestionConcept)
        .where(QuestionConcept.concept_id.in_(concept_ids))
    )
    m = db.scalar(
        select(func.count())
        .select_from(StudentMastery)
        .where(StudentMastery.concept_id.in_(concept_ids))
    )
    return bool(q or m)


def delete_node(db: Session, kind: str, node_id: int) -> None:
    model = {"subject": Subject, "chapter": Chapter, "topic": Topic, "concept": Concept}[kind]
    node = get_or_404(db, model, node_id)
    ids = [node.id] if kind == "concept" else concept_ids_for(db, **{f"{kind}_id": node.id})
    if _has_activity(db, ids):
        raise Conflict(
            "This has questions or student progress attached. Move or archive it instead of "
            "deleting, so learning history is preserved.",
            code="has_activity",
        )
    db.delete(node)


def set_prerequisites(db: Session, concept_id: int, prerequisite_ids: list[int]) -> list[int]:
    concept = get_or_404(db, Concept, concept_id)
    ids = list(dict.fromkeys(prerequisite_ids))
    if concept.id in ids:
        raise AppError("A concept can't be its own prerequisite.", code="self_prerequisite")
    if ids:
        found = set(db.scalars(select(Concept.id).where(Concept.id.in_(ids))))
        if missing := set(ids) - found:
            raise NotFound(f"Unknown concept(s): {sorted(missing)}")
    # Reject cycles: none of the new prerequisites may (transitively) depend on this concept.
    graph = prerequisites_map(db)
    graph[concept.id] = ids
    stack, seen = list(ids), set()
    while stack:
        cur = stack.pop()
        if cur == concept.id:
            raise AppError("That would create a prerequisite loop.", code="prerequisite_cycle")
        if cur in seen:
            continue
        seen.add(cur)
        stack.extend(graph.get(cur, []))
    db.query(ConceptPrerequisite).filter(ConceptPrerequisite.concept_id == concept.id).delete()
    for pid in ids:
        db.add(ConceptPrerequisite(concept_id=concept.id, prerequisite_id=pid))
    return ids


def list_curricula(db: Session) -> list[dict]:
    counts = dict(
        db.execute(
            select(Subject.curriculum_id, func.count(Concept.id))
            .join(Chapter, Chapter.subject_id == Subject.id)
            .join(Topic, Topic.chapter_id == Chapter.id)
            .join(Concept, Concept.topic_id == Topic.id)
            .group_by(Subject.curriculum_id)
        ).all()
    )
    return [
        {
            "id": c.id,
            "name": c.name,
            "version": c.version,
            "status": c.status.value,
            "academic_year": c.academic_year,
            "is_sample": c.is_sample,
            "board": {"id": c.board.id, "name": c.board.name},
            "grade": {"id": c.grade.id, "name": c.grade.name} if c.grade else None,
            "concept_count": counts.get(c.id, 0),
        }
        for c in db.scalars(select(Curriculum).order_by(Curriculum.name, Curriculum.version))
    ]


# ── import / export ──────────────────────────────────────────────────────────


def export(db: Session, curriculum_id: int) -> dict:
    t = tree(db, curriculum_id, include_drafts=True)
    codes = {}
    for s in t["subjects"]:
        for ch in s["chapters"]:
            for tp in ch["topics"]:
                for c in tp["concepts"]:
                    codes[c["id"]] = c["code"]
    descriptions = (
        dict(
            db.execute(
                select(Concept.id, Concept.description).where(Concept.id.in_(list(codes)))
            ).all()
        )
        if codes
        else {}
    )
    return {
        "format": "adaptivelearn.curriculum/v1",
        "name": t["name"],
        "version": t["version"],
        "board": t["board"]["code"],
        "grade": t["grade"]["name"] if t["grade"] else None,
        "subjects": [
            {
                "code": s["code"],
                "name": s["name"],
                "chapters": [
                    {
                        "name": ch["name"],
                        "topics": [
                            {
                                "name": tp["name"],
                                "concepts": [
                                    {
                                        "code": c["code"],
                                        "name": c["name"],
                                        "description": descriptions.get(c["id"], ""),
                                        "prerequisites": [
                                            codes[p] for p in c["prerequisite_ids"] if p in codes
                                        ],
                                    }
                                    for c in tp["concepts"]
                                ],
                            }
                            for tp in ch["topics"]
                        ],
                    }
                    for ch in s["chapters"]
                ],
            }
            for s in t["subjects"]
        ],
    }


def import_curriculum(
    db: Session, data: dict, *, is_sample=False, status=ContentStatus.DRAFT
) -> Curriculum:
    if data.get("format") != "adaptivelearn.curriculum/v1":
        raise AppError(
            "Unsupported file format (expected adaptivelearn.curriculum/v1).", code="bad_format"
        )
    board = db.scalar(select(Board).where(Board.code == data.get("board")))
    if board is None:
        raise AppError(
            f"Unknown board/exam code {data.get('board')!r}. Create it first.", code="unknown_board"
        )
    grade = None
    if data.get("grade"):
        grade = db.scalar(select(Grade).where(Grade.name == data["grade"]))
        if grade is None:
            raise AppError(f"Unknown class {data['grade']!r}.", code="unknown_grade")
    if db.scalar(
        select(Curriculum).where(
            Curriculum.board_id == board.id,
            Curriculum.grade_id == (grade.id if grade else None),
            Curriculum.version == data["version"],
        )
    ):
        raise Conflict(
            "A curriculum with this board, class and version already exists.",
            code="duplicate_curriculum",
        )
    cur = Curriculum(
        board_id=board.id,
        grade_id=grade.id if grade else None,
        name=data["name"],
        version=data["version"],
        status=status,
        is_sample=is_sample,
    )
    db.add(cur)
    db.flush()
    by_code: dict[str, Concept] = {}
    pending: list[tuple[Concept, list[str]]] = []
    for si, s in enumerate(data.get("subjects", [])):
        subj = Subject(curriculum_id=cur.id, code=s["code"], name=s["name"], sequence=si)
        db.add(subj)
        db.flush()
        for ci, ch in enumerate(s.get("chapters", [])):
            chap = Chapter(subject_id=subj.id, name=ch["name"], sequence=ci)
            db.add(chap)
            db.flush()
            for ti, tp in enumerate(ch.get("topics", [])):
                top = Topic(chapter_id=chap.id, name=tp["name"], sequence=ti)
                db.add(top)
                db.flush()
                for ki, c in enumerate(tp.get("concepts", [])):
                    if c["code"] in by_code:
                        raise AppError(
                            f"Duplicate concept code {c['code']!r}.", code="duplicate_code"
                        )
                    con = Concept(
                        topic_id=top.id,
                        code=c["code"],
                        name=c["name"],
                        description=c.get("description", ""),
                        sequence=ki,
                    )
                    db.add(con)
                    by_code[c["code"]] = con
                    pending.append((con, c.get("prerequisites", [])))
    db.flush()
    for con, pres in pending:
        missing = [p for p in pres if p not in by_code]
        if missing:
            raise AppError(
                f"Concept {con.code!r} lists unknown prerequisites {missing}.",
                code="unknown_prerequisite",
            )
        set_prerequisites(db, con.id, [by_code[p].id for p in pres])
    return cur
