"""/api/v1/admin/curriculum — manage boards, classes, curricula and the concept graph."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.config.database import DbSession, transaction
from app.modules.audit import service as audit
from app.modules.curriculum import service
from app.modules.curriculum.models import (
    Board,
    BoardKind,
    Chapter,
    Concept,
    ContentStatus,
    Curriculum,
    Grade,
    StudyMode,
    Subject,
    Topic,
)
from app.shared.exceptions import Conflict
from app.shared.permissions import Principal, require_permission
from app.shared.request import client_ip

router = APIRouter(prefix="/admin/curriculum", tags=["admin: curriculum"])
Manager = Annotated[Principal, Depends(require_permission("curriculum.manage"))]


class BoardIn(BaseModel):
    code: str = Field(min_length=2, max_length=32, pattern=r"^[A-Z0-9_]+$")
    name: str = Field(min_length=2, max_length=120)
    kind: BoardKind
    study_mode: StudyMode


class GradeIn(BaseModel):
    code: str = Field(min_length=1, max_length=16)
    name: str = Field(min_length=1, max_length=40)
    level: int = Field(ge=1, le=20)


class CurriculumIn(BaseModel):
    board_id: int
    grade_id: int | None = None
    name: str = Field(min_length=2, max_length=160)
    version: str = Field(min_length=1, max_length=32)
    academic_year: str | None = Field(default=None, max_length=16)


class CurriculumPatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    version: str | None = Field(default=None, min_length=1, max_length=32)
    academic_year: str | None = Field(default=None, max_length=16)
    status: ContentStatus | None = None


class NodeIn(BaseModel):
    parent_id: int
    name: str = Field(min_length=1, max_length=160)
    code: str | None = Field(default=None, max_length=48)
    description: str | None = Field(default=None, max_length=20000)
    sequence: int | None = Field(default=None, ge=0, le=10000)


class NodePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    code: str | None = Field(default=None, max_length=48)
    description: str | None = Field(default=None, max_length=20000)
    sequence: int | None = Field(default=None, ge=0, le=10000)


class Prerequisites(BaseModel):
    prerequisite_ids: list[int] = Field(max_length=30)


KINDS: dict[str, tuple[type, type | None, str]] = {
    # kind: (model, parent model, parent fk)
    "subjects": (Subject, Curriculum, "curriculum_id"),
    "chapters": (Chapter, Subject, "subject_id"),
    "topics": (Topic, Chapter, "chapter_id"),
    "concepts": (Concept, Topic, "topic_id"),
}


def _log(db, p, request, action, target_type, target_id, details=None):
    audit.record(
        db,
        action,
        actor_user_id=p.user_id,
        target_type=target_type,
        target_id=target_id,
        details=details or {},
        ip=client_ip(request),
    )


@router.get("/boards")
def boards(_: Manager, db: DbSession):
    return [
        {
            "id": b.id,
            "code": b.code,
            "name": b.name,
            "kind": b.kind.value,
            "study_mode": b.study_mode.value,
        }
        for b in db.scalars(select(Board).order_by(Board.name))
    ]


@router.post("/boards", status_code=status.HTTP_201_CREATED)
def create_board(body: BoardIn, request: Request, p: Manager, db: DbSession):
    with transaction(db):
        if db.scalar(select(Board).where(Board.code == body.code)):
            raise Conflict("A board/exam with that code exists.", code="duplicate")
        b = Board(**body.model_dump())
        db.add(b)
        db.flush()
        _log(db, p, request, "curriculum.board_created", "board", b.id, body.model_dump())
    return {"id": b.id}


@router.get("/grades")
def grades(_: Manager, db: DbSession):
    return [
        {"id": g.id, "code": g.code, "name": g.name, "level": g.level}
        for g in db.scalars(select(Grade).order_by(Grade.level))
    ]


@router.post("/grades", status_code=status.HTTP_201_CREATED)
def create_grade(body: GradeIn, request: Request, p: Manager, db: DbSession):
    with transaction(db):
        g = Grade(**body.model_dump())
        db.add(g)
        db.flush()
        _log(db, p, request, "curriculum.grade_created", "grade", g.id, body.model_dump())
    return {"id": g.id}


@router.get("/curricula")
def curricula(_: Manager, db: DbSession):
    return service.list_curricula(db)


@router.post("/curricula", status_code=status.HTTP_201_CREATED)
def create_curriculum(body: CurriculumIn, request: Request, p: Manager, db: DbSession):
    with transaction(db):
        service.get_or_404(db, Board, body.board_id)
        if body.grade_id:
            service.get_or_404(db, Grade, body.grade_id)
        c = Curriculum(**body.model_dump())
        db.add(c)
        db.flush()
        _log(db, p, request, "curriculum.created", "curriculum", c.id, body.model_dump())
    return {"id": c.id}


@router.patch("/curricula/{curriculum_id}")
def update_curriculum(
    curriculum_id: int, body: CurriculumPatch, request: Request, p: Manager, db: DbSession
):
    with transaction(db):
        c = service.get_or_404(db, Curriculum, curriculum_id)
        changes = body.model_dump(exclude_none=True)
        for k, v in changes.items():
            setattr(c, k, v)
        _log(
            db,
            p,
            request,
            "curriculum.updated",
            "curriculum",
            c.id,
            {k: str(v) for k, v in changes.items()},
        )
    return service.list_curricula(db)


@router.get("/curricula/{curriculum_id}/tree")
def curriculum_tree(curriculum_id: int, _: Manager, db: DbSession):
    from app.modules.question_bank.service import published_counts

    t = service.tree(db, curriculum_id, include_drafts=True)
    ids = [
        c["id"]
        for s in t["subjects"]
        for ch in s["chapters"]
        for tp in ch["topics"]
        for c in tp["concepts"]
    ]
    counts = published_counts(db, ids)
    descriptions = (
        dict(db.execute(select(Concept.id, Concept.description).where(Concept.id.in_(ids))).all())
        if ids
        else {}
    )
    for s in t["subjects"]:
        for ch in s["chapters"]:
            for tp in ch["topics"]:
                for c in tp["concepts"]:
                    c["question_count"] = counts.get(c["id"], 0)
                    c["description"] = descriptions.get(c["id"], "")
    return t


@router.get("/curricula/{curriculum_id}/export")
def export_curriculum(curriculum_id: int, _: Manager, db: DbSession):
    return service.export(db, curriculum_id)


@router.post("/curricula/import", status_code=status.HTTP_201_CREATED)
def import_curriculum(body: dict[str, Any], request: Request, p: Manager, db: DbSession):
    with transaction(db):
        c = service.import_curriculum(db, body)
        _log(db, p, request, "curriculum.imported", "curriculum", c.id, {"name": c.name})
    return {"id": c.id}


@router.post("/{kind}", status_code=status.HTTP_201_CREATED)
def create_node(kind: str, body: NodeIn, request: Request, p: Manager, db: DbSession):
    model, parent_model, fk = KINDS.get(kind) or (None, None, None)
    if model is None:
        from app.shared.exceptions import NotFound

        raise NotFound("Unknown curriculum level.")
    with transaction(db):
        service.get_or_404(db, parent_model, body.parent_id)
        fields = {fk: body.parent_id, "name": body.name}
        if body.sequence is not None:
            fields["sequence"] = body.sequence
        if model in (Subject, Concept):
            fields["code"] = (body.code or body.name).strip().upper().replace(" ", "_")[:48]
        if model is Concept:
            fields["description"] = body.description or ""
        node = model(**fields)
        db.add(node)
        db.flush()
        _log(
            db,
            p,
            request,
            f"curriculum.{kind[:-1]}_created",
            kind[:-1],
            node.id,
            {"name": body.name},
        )
    return {"id": node.id}


@router.patch("/{kind}/{node_id}")
def update_node(
    kind: str, node_id: int, body: NodePatch, request: Request, p: Manager, db: DbSession
):
    model = KINDS[kind][0] if kind in KINDS else None
    if model is None:
        from app.shared.exceptions import NotFound

        raise NotFound("Unknown curriculum level.")
    with transaction(db):
        node = service.get_or_404(db, model, node_id)
        changes = body.model_dump(exclude_none=True)
        for k, v in changes.items():
            if hasattr(node, k):
                setattr(node, k, v)
        _log(
            db,
            p,
            request,
            f"curriculum.{kind[:-1]}_updated",
            kind[:-1],
            node.id,
            {k: (v if k != "description" else "…") for k, v in changes.items()},
        )
    return {"id": node.id}


@router.delete("/{kind}/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_node(kind: str, node_id: int, request: Request, p: Manager, db: DbSession):
    if kind not in KINDS:
        from app.shared.exceptions import NotFound

        raise NotFound("Unknown curriculum level.")
    with transaction(db):
        service.delete_node(db, kind[:-1], node_id)
        _log(db, p, request, f"curriculum.{kind[:-1]}_deleted", kind[:-1], node_id)


@router.put("/concepts/{concept_id}/prerequisites")
def set_prerequisites(
    concept_id: int, body: Prerequisites, request: Request, p: Manager, db: DbSession
):
    with transaction(db):
        ids = service.set_prerequisites(db, concept_id, body.prerequisite_ids)
        _log(
            db,
            p,
            request,
            "curriculum.prerequisites_set",
            "concept",
            concept_id,
            {"prerequisite_ids": ids},
        )
    return {"prerequisite_ids": ids}
