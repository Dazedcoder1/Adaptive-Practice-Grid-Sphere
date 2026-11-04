"""Server-side answer evaluation and answer-key validation for every question type.

Pure functions, no database access, so they're easy to test and reuse in mock exams.

Formats (`content` is student-safe, `answer` is server-only):

    mcq_single / diagram / assertion_reason
        content {"options": [{"id": "a", "text": "…"}, …]}      answer {"correct": "b"}
        response {"selected": "b"}
    mcq_multi
        content {"options": […]}         answer {"correct": ["a", "c"], "partial": false}
        response {"selected": ["a", "c"]}
    numerical
        content {"unit": "m/s²"}         answer {"value": 2.5, "tolerance": 0.05}
        response {"value": "2.5"}        (tolerance is absolute; default 1 % of |value|)
    integer
        answer {"value": 4}              response {"value": "4"}
    fill_blank                           stem marks blanks with ___
        content {"blanks": 2}            answer {"accepted": [["inertia"], ["mass", "m"]]}
        response {"values": ["Inertia", "mass"]}
    match
        content {"left": [{id,text}], "right": [{id,text}]}
        answer {"pairs": {"l1": "r3", …}}                       response {"pairs": {…}}
    subjective
        answer {"model_answer": "…"}     response {"text": "…"}  → not auto-graded
"""

import math
import re
from dataclasses import dataclass, field
from typing import Any

from app.modules.question_bank.models import QuestionType

SINGLE_CHOICE = {QuestionType.MCQ_SINGLE, QuestionType.DIAGRAM, QuestionType.ASSERTION_REASON}

# Standard assertion–reason options (CBSE / JEE wording).
ASSERTION_REASON_OPTIONS = [
    {"id": "a", "text": "Both A and R are true, and R is the correct explanation of A."},
    {"id": "b", "text": "Both A and R are true, but R is not the correct explanation of A."},
    {"id": "c", "text": "A is true, but R is false."},
    {"id": "d", "text": "A is false, but R is true."},
]


class InvalidQuestion(ValueError):
    """Raised for an answer key that doesn't fit its question type."""


class InvalidResponse(ValueError):
    """Raised for a submitted response that doesn't fit the question type."""


@dataclass
class EvalResult:
    evaluation: str  # correct | partial | incorrect | ungraded
    score: float  # 0..1
    correct_answer: dict[str, Any] = field(default_factory=dict)  # shown after answering

    @property
    def is_correct(self) -> bool:
        return self.evaluation == "correct"


# ── helpers ──────────────────────────────────────────────────────────────────


def _option_ids(content: dict) -> list[str]:
    opts = content.get("options")
    if not isinstance(opts, list) or len(opts) < 2:
        raise InvalidQuestion("Needs at least two options.")
    ids = [str(o.get("id", "")) for o in opts]
    if any(not i for i in ids) or len(set(ids)) != len(ids):
        raise InvalidQuestion("Every option needs a unique id.")
    if any(not str(o.get("text", "")).strip() for o in opts):
        raise InvalidQuestion("Every option needs text.")
    return ids


def _number(value: Any, what: str = "value") -> float:
    if isinstance(value, bool):
        raise InvalidResponse(f"{what} must be a number.")
    if isinstance(value, int | float):
        f = float(value)
    else:
        text = str(value).strip().replace(",", "").replace("−", "-")
        if not re.fullmatch(r"[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?", text):
            raise InvalidResponse(f"{what} must be a number.")
        f = float(text)
    if not math.isfinite(f):
        raise InvalidResponse(f"{what} must be a finite number.")
    return f


def _norm_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value)).strip().casefold().rstrip(".")


def _blank_matches(given: Any, accepted: list[Any]) -> bool:
    g = _norm_text(given)
    if not g:
        return False
    for a in accepted:
        if _norm_text(a) == g:
            return True
        try:  # numeric blanks: "2" == "2.0"
            if math.isclose(_number(a), _number(g), rel_tol=1e-9, abs_tol=1e-9):
                return True
        except (InvalidResponse, InvalidQuestion):
            pass
    return False


def default_tolerance(value: float) -> float:
    return max(abs(value) * 0.01, 1e-9)


# ── answer-key validation (used when authoring / importing) ──────────────────


def _with_default_options(qtype: QuestionType, content: dict) -> dict:
    if qtype == QuestionType.ASSERTION_REASON and "options" not in content:
        return {**content, "options": ASSERTION_REASON_OPTIONS}
    return content


def validate(qtype: QuestionType, content: dict, answer: dict) -> None:
    content = _with_default_options(qtype, content)
    if qtype in SINGLE_CHOICE:
        ids = _option_ids(content)
        if answer.get("correct") not in ids:
            raise InvalidQuestion("The correct option must be one of the options.")
        if qtype == QuestionType.ASSERTION_REASON and not (
            content.get("assertion") and content.get("reason")
        ):
            raise InvalidQuestion("Assertion–reason questions need an assertion and a reason.")
        if qtype == QuestionType.DIAGRAM and not content.get("image"):
            raise InvalidQuestion("Diagram questions need an image.")
    elif qtype == QuestionType.MCQ_MULTI:
        ids = _option_ids(content)
        correct = answer.get("correct")
        if not isinstance(correct, list) or not correct or not set(correct) <= set(ids):
            raise InvalidQuestion("Pick one or more correct options from the options.")
        if len(set(correct)) != len(correct):
            raise InvalidQuestion("Correct options must not repeat.")
    elif qtype == QuestionType.NUMERICAL:
        try:
            _number(answer.get("value"))
            if "tolerance" in answer and _number(answer["tolerance"]) < 0:
                raise InvalidQuestion("Tolerance can't be negative.")
        except InvalidResponse as e:
            raise InvalidQuestion(str(e)) from e
    elif qtype == QuestionType.INTEGER:
        v = answer.get("value")
        if not isinstance(v, int) or isinstance(v, bool):
            raise InvalidQuestion("Integer questions need a whole-number answer.")
    elif qtype == QuestionType.FILL_BLANK:
        accepted = answer.get("accepted")
        blanks = content.get("blanks")
        if not isinstance(accepted, list) or not accepted:
            raise InvalidQuestion("List the accepted answers for each blank.")
        if blanks != len(accepted):
            raise InvalidQuestion("The number of blanks must match the accepted answers.")
        if any(
            not isinstance(a, list) or not a or any(not str(x).strip() for x in a) for a in accepted
        ):
            raise InvalidQuestion("Every blank needs at least one accepted answer.")
    elif qtype == QuestionType.MATCH:
        left, right = content.get("left"), content.get("right")
        if not isinstance(left, list) or not isinstance(right, list) or len(left) < 2:
            raise InvalidQuestion("Match questions need two columns with at least two rows.")
        lids = {str(x.get("id")) for x in left}
        rids = {str(x.get("id")) for x in right}
        pairs = answer.get("pairs")
        if not isinstance(pairs, dict) or set(pairs) != lids or not set(pairs.values()) <= rids:
            raise InvalidQuestion("Pair every left item with an item from the right column.")
    elif qtype == QuestionType.SUBJECTIVE:
        if not str(answer.get("model_answer", "")).strip():
            raise InvalidQuestion("Subjective questions need a model answer.")
    else:  # pragma: no cover
        raise InvalidQuestion(f"Unsupported question type {qtype}.")


# ── evaluation ───────────────────────────────────────────────────────────────


def evaluate(qtype: QuestionType, content: dict, answer: dict, response: dict) -> EvalResult:
    if not isinstance(response, dict):
        raise InvalidResponse("Response must be an object.")
    content = _with_default_options(qtype, content)

    if qtype in SINGLE_CHOICE:
        selected = response.get("selected")
        if selected not in _option_ids(content):
            raise InvalidResponse("Choose one of the options.")
        ok = selected == answer["correct"]
        return EvalResult(
            "correct" if ok else "incorrect", float(ok), {"correct": answer["correct"]}
        )

    if qtype == QuestionType.MCQ_MULTI:
        selected = response.get("selected")
        ids = set(_option_ids(content))
        if not isinstance(selected, list) or not selected or not set(selected) <= ids:
            raise InvalidResponse("Choose one or more of the options.")
        chosen, correct = set(selected), set(answer["correct"])
        reveal = {"correct": sorted(correct)}
        if chosen == correct:
            return EvalResult("correct", 1.0, reveal)
        if answer.get("partial") and chosen < correct:
            return EvalResult("partial", len(chosen) / len(correct), reveal)
        return EvalResult("incorrect", 0.0, reveal)

    if qtype == QuestionType.NUMERICAL:
        given = _number(response.get("value"), "Answer")
        target = _number(answer["value"])
        tol = _number(answer["tolerance"]) if "tolerance" in answer else default_tolerance(target)
        ok = abs(given - target) <= tol + 1e-12
        return EvalResult(
            "correct" if ok else "incorrect",
            float(ok),
            {"value": target, "unit": content.get("unit")},
        )

    if qtype == QuestionType.INTEGER:
        given = _number(response.get("value"), "Answer")
        if not given.is_integer():
            raise InvalidResponse("Enter a whole number.")
        ok = int(given) == answer["value"]
        return EvalResult("correct" if ok else "incorrect", float(ok), {"value": answer["value"]})

    if qtype == QuestionType.FILL_BLANK:
        values = response.get("values")
        accepted = answer["accepted"]
        if not isinstance(values, list) or len(values) != len(accepted):
            raise InvalidResponse(f"Fill all {len(accepted)} blank(s).")
        hits = sum(_blank_matches(v, a) for v, a in zip(values, accepted, strict=True))
        reveal = {"accepted": [a[0] for a in accepted]}
        if hits == len(accepted):
            return EvalResult("correct", 1.0, reveal)
        return EvalResult("partial" if hits else "incorrect", hits / len(accepted), reveal)

    if qtype == QuestionType.MATCH:
        pairs = response.get("pairs")
        key = answer["pairs"]
        if not isinstance(pairs, dict) or set(pairs) != set(key):
            raise InvalidResponse("Match every item on the left.")
        hits = sum(pairs[k] == v for k, v in key.items())
        reveal = {"pairs": key}
        if hits == len(key):
            return EvalResult("correct", 1.0, reveal)
        return EvalResult("partial" if hits else "incorrect", hits / len(key), reveal)

    if qtype == QuestionType.SUBJECTIVE:
        text = str(response.get("text", "")).strip()
        if not text:
            raise InvalidResponse("Write your answer before submitting.")
        if len(text) > 10_000:
            raise InvalidResponse("Answer is too long (10,000 characters max).")
        return EvalResult("ungraded", 0.0, {"model_answer": answer.get("model_answer", "")})

    raise InvalidResponse(f"Unsupported question type {qtype}.")  # pragma: no cover


def student_content(qtype: QuestionType, content: dict) -> dict:
    """What a student may see before answering. Never includes answer data."""
    safe = {
        k: v
        for k, v in content.items()
        if k
        in {
            "options",
            "unit",
            "blanks",
            "left",
            "right",
            "image",
            "image_alt",
            "assertion",
            "reason",
        }
    }
    if qtype == QuestionType.ASSERTION_REASON and "options" not in safe:
        safe["options"] = ASSERTION_REASON_OPTIONS
    return safe
