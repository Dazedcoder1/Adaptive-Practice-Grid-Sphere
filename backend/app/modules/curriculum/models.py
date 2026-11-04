"""Curriculum: Board/Exam → Curriculum version (board + class + year) → Subject → Chapter
→ Topic → Concept, plus the concept prerequisite graph.

A curriculum row is one *version* of a syllabus. Student activity points at concepts, which
belong to exactly one curriculum version, so history stays tied to the syllabus it happened
under when a new version is published.
"""

from enum import StrEnum

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base, TimestampMixin


class BoardKind(StrEnum):
    BOARD = "board"  # school boards: CBSE, ICSE, state boards
    EXAM = "exam"  # competitive exams: JEE Main, JEE Advanced, NEET


class StudyMode(StrEnum):
    SCHOOL = "school"
    JEE = "jee"
    NEET = "neet"


class ContentStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


def _enum(e, name):
    return Enum(e, name=name, values_callable=lambda x: [m.value for m in x])


class Board(TimestampMixin, Base):
    __tablename__ = "boards"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    kind: Mapped[BoardKind] = mapped_column(_enum(BoardKind, "board_kind"), nullable=False)
    study_mode: Mapped[StudyMode] = mapped_column(_enum(StudyMode, "study_mode"), nullable=False)
    country: Mapped[str] = mapped_column(String(2), default="IN", nullable=False)


class Grade(TimestampMixin, Base):
    """A school class (6–12). Named Grade in code to avoid clashing with Python's `class`."""

    __tablename__ = "grades"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)  # "11"
    name: Mapped[str] = mapped_column(String(40), nullable=False)  # "Class 11"
    level: Mapped[int] = mapped_column(Integer, nullable=False)


class Curriculum(TimestampMixin, Base):
    __tablename__ = "curricula"

    id: Mapped[int] = mapped_column(primary_key=True)
    board_id: Mapped[int] = mapped_column(ForeignKey("boards.id"), nullable=False, index=True)
    grade_id: Mapped[int | None] = mapped_column(ForeignKey("grades.id"))
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)  # "2026-27"
    academic_year: Mapped[str | None] = mapped_column(String(16))
    status: Mapped[ContentStatus] = mapped_column(
        _enum(ContentStatus, "content_status"), default=ContentStatus.DRAFT, nullable=False
    )
    is_sample: Mapped[bool] = mapped_column(default=False, nullable=False)

    board: Mapped[Board] = relationship(lazy="joined")
    grade: Mapped[Grade | None] = relationship(lazy="joined")

    __table_args__ = (UniqueConstraint("board_id", "grade_id", "version"),)


class Subject(TimestampMixin, Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    curriculum_id: Mapped[int] = mapped_column(
        ForeignKey("curricula.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    sequence: Mapped[int] = mapped_column(default=0, nullable=False)

    __table_args__ = (UniqueConstraint("curriculum_id", "code"),)


class Chapter(TimestampMixin, Base):
    __tablename__ = "chapters"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    sequence: Mapped[int] = mapped_column(default=0, nullable=False)


class Topic(TimestampMixin, Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    chapter_id: Mapped[int] = mapped_column(
        ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    sequence: Mapped[int] = mapped_column(default=0, nullable=False)


class Concept(TimestampMixin, Base):
    __tablename__ = "concepts"

    id: Mapped[int] = mapped_column(primary_key=True)
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(48), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    # Markdown with $…$ / $$…$$ maths, shown to students on the concept page.
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    sequence: Mapped[int] = mapped_column(default=0, nullable=False)

    __table_args__ = (UniqueConstraint("topic_id", "code"),)


class ConceptPrerequisite(Base):
    __tablename__ = "concept_prerequisites"

    concept_id: Mapped[int] = mapped_column(
        ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True
    )
    prerequisite_id: Mapped[int] = mapped_column(
        ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True, index=True
    )

    __table_args__ = (CheckConstraint("concept_id <> prerequisite_id", name="not_self"),)
