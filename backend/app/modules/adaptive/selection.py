"""Next-question selection — deterministic ranking with controlled exploration (design §6.3).

Pure function over plain data so every decision can be unit-tested and replayed. The
returned `reason` is stored with the delivered question, so each choice is explainable
and auditable ("why did I get this question?").

Policy, in order:
1. Rank concepts by need: lower mastery first, unpractised concepts before mastered
   ones, small bonus for not having been practised recently; concepts served in the last
   two positions of this session are pushed down (no endless loop on one spot).
2. Foundations first — a concept is *ready* once every in-scope prerequisite has been
   practised and isn't weak. If the chosen concept isn't ready, walk back to the
   prerequisite that blocks it: a weak one is remediated ("prerequisite_remediation"), an
   unpractised one is introduced ("prerequisite_first").
3. With probability EXPLORATION, pick a random *ready* concept instead (seeded, so the
   same session + position always reproduces the same decision).
4. Target difficulty follows mastery (1 … 5) and nudges ±1 on recent results in-session.
5. Choose a question for that concept: never repeat within the session, prefer questions
   the student hasn't seen, then the least recently seen; closest to target difficulty.
"""

import random
from dataclasses import dataclass, field
from datetime import datetime

EXPLORATION = 0.15
PREREQ_WEAK_BELOW = 0.45  # remediate a prerequisite only when clearly weak (with evidence)
UNSEEN_PRIOR = 0.2  # mastery assumed for a concept with no attempts (matches BKT P(L0))


@dataclass(frozen=True)
class Candidate:
    question_id: str
    version_id: str
    difficulty: int
    concept_ids: tuple[int, ...]


@dataclass(frozen=True)
class ConceptState:
    p_known: float | None  # None = never practised
    attempts: int = 0
    last_practiced_at: datetime | None = None


@dataclass
class SelectionInput:
    seed: str  # session id + position → reproducible exploration
    scope_concepts: list[int]  # in curriculum order
    candidates: list[Candidate]
    mastery: dict[int, ConceptState]
    prerequisites: dict[int, list[int]]  # concept → its prerequisites
    session_question_ids: set[str] = field(default_factory=set)
    recent_concepts: list[int] = field(default_factory=list)  # this session, oldest→newest
    recent_results: dict[int, list[bool]] = field(default_factory=dict)  # per concept, session
    last_seen: dict[str, datetime] = field(default_factory=dict)  # question → last attempt
    now: datetime | None = None
    exploration: float = EXPLORATION


@dataclass
class Decision:
    candidate: Candidate
    concept_id: int
    target_difficulty: int
    reason: dict


def target_difficulty(p_known: float | None, recent: list[bool]) -> int:
    base = 1 + round(4 * (UNSEEN_PRIOR if p_known is None else p_known))
    if len(recent) >= 2 and recent[-1] and recent[-2]:
        base += 1  # on a streak: stretch
    elif recent and not recent[-1]:
        base -= 1  # just missed one: ease off
    return max(1, min(5, base))


def _p(state: ConceptState | None) -> float:
    return UNSEEN_PRIOR if state is None or state.p_known is None else state.p_known


def _need(cid: int, inp: SelectionInput) -> float:
    st = inp.mastery.get(cid)
    score = 1 - _p(st)
    if st and st.attempts and st.p_known is not None and st.p_known >= 0.9:
        score -= 0.3  # mastered: occasional review only
    if inp.now and st and st.last_practiced_at:
        days = (inp.now - st.last_practiced_at).total_seconds() / 86400
        score += min(days, 14) / 140  # up to +0.1 for not practised in two weeks
    if cid in inp.recent_concepts[-2:]:
        score -= 0.5  # diversity
    return score


def _pick_question(cid: int, target: int, inp: SelectionInput, rng: random.Random):
    pool = [
        c
        for c in inp.candidates
        if cid in c.concept_ids and c.question_id not in inp.session_question_ids
    ]
    if not pool:
        return None
    floor = datetime.min.replace(tzinfo=inp.now.tzinfo if inp.now else None)

    def key(c: Candidate):
        seen = inp.last_seen.get(c.question_id)
        return (seen is not None, seen or floor, abs(c.difficulty - target), rng.random())

    return min(pool, key=key)


def _ready(cid: int, inp: SelectionInput, available: set[int]) -> bool:
    for p in inp.prerequisites.get(cid, []):
        if p not in available:
            continue  # no questions for it in scope — it can't block practice
        st = inp.mastery.get(p)
        if st is None or st.attempts == 0 or _p(st) < PREREQ_WEAK_BELOW:
            return False
    return True


def _foundation(concept: int, inp: SelectionInput, available: set[int], order: list[int]):
    """Follow unready prerequisites back to the one to practise now.
    Returns (concept, rule or None). Weak-with-evidence beats never-practised."""
    rule, seen = None, {concept}
    while not _ready(concept, inp, available):
        blockers = [
            p for p in inp.prerequisites.get(concept, []) if p in available and p not in seen
        ]
        weak = [p for p in blockers if (st := inp.mastery.get(p)) and st.attempts > 0]
        unseen = [p for p in blockers if p not in weak]
        if weak and any(_p(inp.mastery.get(p)) < PREREQ_WEAK_BELOW for p in weak):
            concept = min(weak, key=lambda p: _p(inp.mastery.get(p)))
            rule = "prerequisite_remediation"
        elif unseen:
            concept = min(unseen, key=order.index)
            rule = rule or "prerequisite_first"
        else:
            break  # cycle guard
        seen.add(concept)
    return concept, rule


def select_next(inp: SelectionInput) -> Decision | None:
    rng = random.Random(inp.seed)
    available = {
        cid
        for cid in inp.scope_concepts
        if any(
            cid in c.concept_ids and c.question_id not in inp.session_question_ids
            for c in inp.candidates
        )
    }
    if not available:
        return None
    order = [c for c in inp.scope_concepts if c in available]

    ready = [c for c in order if _ready(c, inp, available)] or order
    explored = rng.random() < inp.exploration and len(ready) > 1
    blocked = None
    if explored:
        concept = rng.choice(ready)
        rule = "exploration"
    else:
        wanted = max(order, key=lambda c: (_need(c, inp), -order.index(c)))
        concept, via = _foundation(wanted, inp, available, order)
        rule = via or "lowest_mastery"
        if via:
            blocked = wanted

    st = inp.mastery.get(concept)
    target = target_difficulty(
        None if st is None else st.p_known, inp.recent_results.get(concept, [])
    )
    cand = _pick_question(concept, target, inp, rng)
    if cand is None:  # pragma: no cover — `available` guarantees a pool
        return None
    reason = {
        "rule": rule,
        "concept_id": concept,
        "mastery": None if st is None else st.p_known,
        "target_difficulty": target,
        "question_difficulty": cand.difficulty,
        "unseen": cand.question_id not in inp.last_seen,
    }
    if blocked is not None:
        reason["for_concept_id"] = blocked
    return Decision(cand, concept, target, reason)


def select_diagnostic(inp: SelectionInput) -> Decision | None:
    """Diagnostic: one question per concept, in curriculum order, at middle difficulty."""
    done = set(inp.recent_concepts)
    rng = random.Random(inp.seed)
    for cid in inp.scope_concepts:
        if cid in done:
            continue
        cand = _pick_question(cid, 3, inp, rng)
        if cand:
            return Decision(
                cand,
                cid,
                3,
                {
                    "rule": "diagnostic",
                    "concept_id": cid,
                    "target_difficulty": 3,
                    "question_difficulty": cand.difficulty,
                },
            )
    return None
