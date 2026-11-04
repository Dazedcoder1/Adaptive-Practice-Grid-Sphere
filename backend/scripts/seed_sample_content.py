"""Load SAMPLE content: classes 6–12, CBSE / JEE Main / NEET, and a published CBSE Class 11
Physics curriculum (Laws of Motion) with ~35 published questions.

    python -m scripts.seed_sample_content

Safe to run more than once — it skips anything that already exists. Everything is flagged
as sample content; archive or edit it in the admin portal.
"""

import sys

from sqlalchemy import select

from app.config.database import SessionLocal, transaction
from app.modules.curriculum import service as curriculum
from app.modules.curriculum.models import (
    Board,
    BoardKind,
    Concept,
    ContentStatus,
    Curriculum,
    Grade,
    StudyMode,
    Subject,
)
from app.modules.question_bank import service as qbank
from app.modules.question_bank.models import QuestionType
from app.seed.laws_of_motion import CURRICULUM, QUESTIONS

BOARDS = [
    ("CBSE", "CBSE", BoardKind.BOARD, StudyMode.SCHOOL),
    ("JEE_MAIN", "JEE Main", BoardKind.EXAM, StudyMode.JEE),
    ("NEET", "NEET (UG)", BoardKind.EXAM, StudyMode.NEET),
]


def seed(db) -> dict:
    created = {"grades": 0, "boards": 0, "curriculum": False, "questions": 0}
    for level in range(6, 13):
        if not db.scalar(select(Grade).where(Grade.code == str(level))):
            db.add(Grade(code=str(level), name=f"Class {level}", level=level))
            created["grades"] += 1
    for code, name, kind, mode in BOARDS:
        if not db.scalar(select(Board).where(Board.code == code)):
            db.add(Board(code=code, name=name, kind=kind, study_mode=mode))
            created["boards"] += 1
    db.flush()

    cur = db.scalar(select(Curriculum).where(Curriculum.version == CURRICULUM["version"]))
    if cur is None:
        cur = curriculum.import_curriculum(
            db, CURRICULUM, is_sample=True, status=ContentStatus.PUBLISHED
        )
        created["curriculum"] = True
    db.flush()

    concept_ids = curriculum.concept_ids_for(db, curriculum_id=cur.id)
    by_code = dict(
        db.execute(select(Concept.code, Concept.id).where(Concept.id.in_(concept_ids))).all()
    )
    if qbank.published_counts(db, concept_ids):
        return created  # questions already loaded
    for q in QUESTIONS:
        data = qbank.QuestionInput(
            type=QuestionType(q["type"]),
            difficulty=q["difficulty"],
            stem=q["stem"],
            content=q["content"],
            answer=q["answer"],
            solution=q["solution"],
            hints=q["hints"],
            estimated_seconds=q["estimated_seconds"],
            source="AdaptiveLearn sample content",
            concepts=[(by_code[c], w) for c, w in q["concepts"]],
        )
        question = qbank.create(db, data, None, is_sample=True)
        qbank.publish(db, question, None, note="sample content")
        created["questions"] += 1
    return created


def main() -> int:
    with SessionLocal() as db, transaction(db):
        result = seed(db)
        subjects = db.scalars(select(Subject.name)).all()
    print("✓ Sample content ready:", result, "subjects:", sorted(set(subjects)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
