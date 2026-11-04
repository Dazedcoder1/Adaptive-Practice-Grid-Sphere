"""Pure-function tests: evaluation, BKT, adaptive selection, spaced repetition."""

from datetime import UTC, datetime, timedelta

import pytest

from app.modules.adaptive.selection import (
    Candidate,
    ConceptState,
    SelectionInput,
    select_diagnostic,
    select_next,
    target_difficulty,
)
from app.modules.knowledge_model import bkt
from app.modules.question_bank.evaluation import (
    InvalidQuestion,
    InvalidResponse,
    evaluate,
    student_content,
    validate,
)
from app.modules.question_bank.models import QuestionType as T
from app.modules.revision.scheduler import next_schedule, retention_estimate

OPTS = {"options": [{"id": "a", "text": "1"}, {"id": "b", "text": "2"}, {"id": "c", "text": "3"}]}


# ── evaluation ───────────────────────────────────────────────────────────────


class TestEvaluation:
    def test_single_choice(self):
        assert evaluate(T.MCQ_SINGLE, OPTS, {"correct": "b"}, {"selected": "b"}).is_correct
        r = evaluate(T.MCQ_SINGLE, OPTS, {"correct": "b"}, {"selected": "a"})
        assert r.evaluation == "incorrect" and r.correct_answer == {"correct": "b"}
        with pytest.raises(InvalidResponse):
            evaluate(T.MCQ_SINGLE, OPTS, {"correct": "b"}, {"selected": "z"})

    def test_multi_select_exact_and_partial(self):
        key = {"correct": ["a", "c"]}
        assert evaluate(T.MCQ_MULTI, OPTS, key, {"selected": ["c", "a"]}).score == 1
        assert evaluate(T.MCQ_MULTI, OPTS, key, {"selected": ["a"]}).score == 0
        partial = evaluate(T.MCQ_MULTI, OPTS, {**key, "partial": True}, {"selected": ["a"]})
        assert partial.evaluation == "partial" and partial.score == 0.5
        wrong = evaluate(T.MCQ_MULTI, OPTS, {**key, "partial": True}, {"selected": ["a", "b"]})
        assert wrong.score == 0  # any wrong option → no credit

    def test_numerical_tolerance_and_parsing(self):
        key = {"value": 2.5, "tolerance": 0.05}
        assert evaluate(T.NUMERICAL, {}, key, {"value": "2.54"}).is_correct
        assert not evaluate(T.NUMERICAL, {}, key, {"value": "2.6"}).is_correct
        assert evaluate(T.NUMERICAL, {}, {"value": 1000}, {"value": "1,005"}).is_correct  # 1 %
        assert evaluate(T.NUMERICAL, {}, {"value": -9.8}, {"value": "−9.8"}).is_correct
        for bad in ("abc", "", "1e999", None):
            with pytest.raises(InvalidResponse):
                evaluate(T.NUMERICAL, {}, key, {"value": bad})

    def test_integer(self):
        assert evaluate(T.INTEGER, {}, {"value": 4}, {"value": "4"}).is_correct
        assert evaluate(T.INTEGER, {}, {"value": 4}, {"value": "4.0"}).is_correct
        with pytest.raises(InvalidResponse):
            evaluate(T.INTEGER, {}, {"value": 4}, {"value": "4.5"})

    def test_fill_blank_is_case_and_space_insensitive_with_partial_credit(self):
        key = {"accepted": [["inertia"], ["mass", "m"]]}
        c = {"blanks": 2}
        assert evaluate(T.FILL_BLANK, c, key, {"values": ["  Inertia ", "M"]}).is_correct
        half = evaluate(T.FILL_BLANK, c, key, {"values": ["inertia", "weight"]})
        assert half.evaluation == "partial" and half.score == 0.5
        assert evaluate(
            T.FILL_BLANK, {"blanks": 1}, {"accepted": [["2"]]}, {"values": ["2.0"]}
        ).is_correct

    def test_match(self):
        c = {"left": [{"id": "1"}, {"id": "2"}], "right": [{"id": "x"}, {"id": "y"}]}
        key = {"pairs": {"1": "y", "2": "x"}}
        assert evaluate(T.MATCH, c, key, {"pairs": {"1": "y", "2": "x"}}).is_correct
        assert evaluate(T.MATCH, c, key, {"pairs": {"1": "y", "2": "y"}}).score == 0.5
        with pytest.raises(InvalidResponse):
            evaluate(T.MATCH, c, key, {"pairs": {"1": "y"}})

    def test_subjective_is_stored_not_graded(self):
        r = evaluate(T.SUBJECTIVE, {}, {"model_answer": "m"}, {"text": "my answer"})
        assert r.evaluation == "ungraded" and r.score == 0

    def test_validation_rejects_bad_keys(self):
        with pytest.raises(InvalidQuestion):
            validate(T.MCQ_SINGLE, OPTS, {"correct": "z"})
        with pytest.raises(InvalidQuestion):
            validate(T.FILL_BLANK, {"blanks": 2}, {"accepted": [["a"]]})
        with pytest.raises(InvalidQuestion):
            validate(T.INTEGER, {}, {"value": 2.5})
        with pytest.raises(InvalidQuestion):
            validate(T.DIAGRAM, OPTS, {"correct": "a"})  # no image
        validate(T.MCQ_MULTI, OPTS, {"correct": ["a", "b"]})

    def test_student_content_never_contains_answers(self):
        content = {**OPTS, "answer": "b", "correct": "b", "solution": "x"}
        safe = student_content(T.MCQ_SINGLE, content)
        assert set(safe) == {"options"}
        ar = student_content(T.ASSERTION_REASON, {"assertion": "A", "reason": "R"})
        assert len(ar["options"]) == 4


# ── BKT ──────────────────────────────────────────────────────────────────────


class TestBKT:
    def test_correct_raises_and_incorrect_lowers(self):
        p = 0.4
        up = bkt.update(p, score=1, question_type="numerical")
        down = bkt.update(p, score=0, question_type="numerical")
        assert up > p > down

    def test_matches_textbook_formula(self):
        p, s, g, t = 0.3, 0.1, 0.25, 0.15
        posterior = p * (1 - s) / (p * (1 - s) + (1 - p) * g)
        expected = posterior + (1 - posterior) * t
        assert bkt.update(p, score=1, question_type="mcq_single") == pytest.approx(expected, 1e-5)

    def test_guessable_types_are_weaker_evidence(self):
        mcq = bkt.update(0.3, score=1, question_type="mcq_single")
        num = bkt.update(0.3, score=1, question_type="numerical")
        assert num > mcq

    def test_hints_and_weights_dampen(self):
        full = bkt.update(0.3, score=1, question_type="numerical")
        hinted = bkt.update(0.3, score=1, question_type="numerical", hints_used=2)
        weighted = bkt.update(0.3, score=1, question_type="numerical", concept_weight=0.5)
        assert 0.3 < hinted < full and 0.3 < weighted < full

    def test_converges_with_practice_and_stays_in_bounds(self):
        p = bkt.PARAMS.p_init
        for _ in range(8):
            p = bkt.update(p, score=1, question_type="numerical")
        assert 0.95 < p < 1
        for _ in range(20):
            p = bkt.update(p, score=0, question_type="mcq_single")
        assert 0 < p < 0.5

    def test_levels(self):
        assert bkt.level(None, 0) == "not_started"
        assert bkt.level(0.95, 2) == "proficient"  # not enough evidence for mastered
        assert bkt.level(0.95, 3) == "mastered"
        assert bkt.level(0.3, 4) == "weak"


# ── adaptive selection ───────────────────────────────────────────────────────

NOW = datetime(2026, 11, 4, tzinfo=UTC)


def cands():
    out = []
    for cid in (1, 2, 3):
        for d in (1, 3, 5):
            out.append(Candidate(f"q{cid}{d}", f"v{cid}{d}", d, (cid,)))
    return out


def inp(**kw):
    base = dict(
        seed="s",
        scope_concepts=[1, 2, 3],
        candidates=cands(),
        mastery={},
        prerequisites={},
        now=NOW,
        exploration=0.0,
    )
    base.update(kw)
    return SelectionInput(**base)


class TestSelection:
    def test_targets_lowest_mastery_and_records_reason(self):
        m = {1: ConceptState(0.8, 5), 2: ConceptState(0.3, 5), 3: ConceptState(0.6, 5)}
        d = select_next(inp(mastery=m))
        assert d.concept_id == 2 and d.reason["rule"] == "lowest_mastery"
        assert d.reason["target_difficulty"] == target_difficulty(0.3, [])

    def test_prerequisite_remediation(self):
        m = {1: ConceptState(0.3, 4), 2: ConceptState(0.1, 2), 3: ConceptState(0.9, 9)}
        d = select_next(inp(mastery=m, prerequisites={2: [1]}))
        assert d.concept_id == 1
        assert d.reason["rule"] == "prerequisite_remediation" and d.reason["for_concept_id"] == 2

    def test_unpractised_prerequisite_comes_first(self):
        # A new student: concept 2 needs 1. Even if 2 ranks first, start with 1.
        m = {2: ConceptState(0.1, 1)}
        d = select_next(inp(mastery=m, prerequisites={2: [1]}))
        assert d.concept_id == 1
        assert d.reason["rule"] == "prerequisite_first" and d.reason["for_concept_id"] == 2

    def test_follows_the_prerequisite_chain_to_the_root(self):
        m = {3: ConceptState(0.05, 2)}
        d = select_next(inp(mastery=m, prerequisites={3: [2], 2: [1]}))
        assert d.concept_id == 1 and d.reason["for_concept_id"] == 3

    def test_ready_concepts_are_served_directly(self):
        m = {1: ConceptState(0.7, 4), 2: ConceptState(0.2, 2)}
        d = select_next(inp(mastery=m, prerequisites={2: [1]}))
        assert d.concept_id == 2 and d.reason["rule"] == "lowest_mastery"

    def test_prerequisite_without_questions_does_not_block(self):
        only_2 = [c for c in cands() if c.concept_ids == (2,)]
        d = select_next(inp(scope_concepts=[2], candidates=only_2, prerequisites={2: [1]}))
        assert d.concept_id == 2

    def test_exploration_only_picks_ready_concepts(self):
        # 2 and 3 depend on 1, which is unpractised: exploration may only choose 1.
        for seed in ("a", "b", "c", "d", "e", "f"):
            d = select_next(inp(seed=seed, exploration=1.0, prerequisites={2: [1], 3: [1]}))
            assert d.concept_id == 1, seed

    def test_never_repeats_a_question_in_session_and_prefers_unseen(self):
        seen = {"q21": NOW - timedelta(days=1)}
        d = select_next(
            inp(
                scope_concepts=[2],
                session_question_ids={"q23"},
                last_seen=seen,
                mastery={2: ConceptState(0.5, 3)},
            )
        )
        assert d.candidate.question_id == "q25"  # q23 used, q21 seen → unseen q25

    def test_diversity_avoids_hammering_one_concept(self):
        m = {1: ConceptState(0.5, 5), 2: ConceptState(0.4, 5), 3: ConceptState(0.55, 5)}
        d = select_next(inp(mastery=m, recent_concepts=[2, 2]))
        assert d.concept_id != 2

    def test_exploration_is_reproducible(self):
        a = select_next(inp(seed="abc", exploration=1.0))
        b = select_next(inp(seed="abc", exploration=1.0))
        assert a.reason["rule"] == "exploration" and a.candidate == b.candidate
        # with only one ready concept there's nothing to explore
        one = select_next(inp(seed="abc", exploration=1.0, prerequisites={2: [1], 3: [1]}))
        assert one.reason["rule"] != "exploration"

    def test_difficulty_follows_mastery_and_streaks(self):
        assert target_difficulty(None, []) == 2
        assert target_difficulty(0.9, []) == 5
        assert target_difficulty(0.5, [True, True]) == 4
        assert target_difficulty(0.5, [False]) == 2

    def test_returns_none_when_exhausted(self):
        used = {c.question_id for c in cands()}
        assert select_next(inp(session_question_ids=used)) is None

    def test_diagnostic_covers_each_concept_once_in_order(self):
        d1 = select_diagnostic(inp())
        d2 = select_diagnostic(inp(recent_concepts=[1]))
        assert (d1.concept_id, d2.concept_id) == (1, 2)
        assert d1.candidate.difficulty == 3


# ── spaced repetition ────────────────────────────────────────────────────────


class TestRevision:
    def test_intervals_grow_and_lapse_resets(self):
        s1 = next_schedule(None, correct=True, now=NOW)
        s2 = next_schedule(s1, correct=True, now=NOW)
        s3 = next_schedule(s2, correct=True, now=NOW)
        assert (s1.interval_days, s2.interval_days) == (1, 3) and s3.interval_days > 6
        lapse = next_schedule(s3, correct=False, now=NOW)
        assert lapse.interval_days == 1 and lapse.lapses == 1 and lapse.ease < s3.ease
        assert lapse.due_at == NOW + timedelta(days=1)

    def test_retention_is_about_90_percent_at_due_date(self):
        assert retention_estimate(4, NOW - timedelta(days=4), NOW) == pytest.approx(0.9, 0.01)
        assert retention_estimate(4, None, NOW) is None


def test_assertion_reason_uses_standard_options_without_storing_them():
    c = {"assertion": "A", "reason": "R"}
    validate(T.ASSERTION_REASON, c, {"correct": "a"})
    assert evaluate(T.ASSERTION_REASON, c, {"correct": "a"}, {"selected": "a"}).is_correct
