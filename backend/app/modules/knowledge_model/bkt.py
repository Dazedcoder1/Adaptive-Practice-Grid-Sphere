"""Bayesian Knowledge Tracing — versioned and side-effect free.

    P(L | correct)   = P(L)(1 − S) / [P(L)(1 − S) + (1 − P(L)) G]
    P(L | incorrect) = P(L) S       / [P(L) S       + (1 − P(L)) (1 − G)]
    P(L')            = P(L | obs) + (1 − P(L | obs)) T

Extensions, all deterministic:
- Partial credit s ∈ [0,1] mixes the two posteriors: s·P(L|correct) + (1−s)·P(L|incorrect).
- Answers given after revealing hints count as weaker evidence.
- A question tagged to several concepts updates each in proportion to its tag weight.

Parameters are initial, author-set values — not yet fitted to data. Treat P(L) as a mastery
*estimate*, not a calibrated probability, until it's validated (design §6.1). Changing any
parameter means a new MODEL_VERSION; stored history keeps the version that produced it.
"""

from dataclasses import dataclass

MODEL_VERSION = "bkt-v1"


@dataclass(frozen=True)
class BKTParams:
    p_init: float = 0.2  # P(L0)
    p_learn: float = 0.15  # P(T)
    p_slip: float = 0.1  # P(S)
    p_guess: float = 0.2  # P(G) — overridden per question type below


# Guessing is easier on 4-option MCQs than on a numerical answer.
GUESS_BY_TYPE = {
    "mcq_single": 0.25,
    "diagram": 0.25,
    "assertion_reason": 0.25,
    "mcq_multi": 0.1,
    "match": 0.1,
    "fill_blank": 0.08,
    "numerical": 0.04,
    "integer": 0.04,
}

PARAMS = BKTParams()

# Mastery levels (on P(L)). "mastered" also needs enough evidence.
WEAK_BELOW = 0.4
DEVELOPING_BELOW = 0.7
MASTERED_AT = 0.9
MASTERED_MIN_ATTEMPTS = 3


def _posterior(p: float, correct: bool, slip: float, guess: float) -> float:
    if correct:
        num, den = p * (1 - slip), p * (1 - slip) + (1 - p) * guess
    else:
        num, den = p * slip, p * slip + (1 - p) * (1 - guess)
    return num / den if den > 0 else p


def update(
    p_known: float,
    *,
    score: float,
    question_type: str,
    hints_used: int = 0,
    concept_weight: float = 1.0,
    params: BKTParams = PARAMS,
) -> float:
    """New P(L) after one graded answer. `score` is 0..1 (partial credit allowed)."""
    p = min(max(p_known, 1e-4), 1 - 1e-4)
    guess = GUESS_BY_TYPE.get(question_type, params.p_guess)
    observed = score * _posterior(p, True, params.p_slip, guess) + (1 - score) * _posterior(
        p, False, params.p_slip, guess
    )
    # Hints weaken evidence of knowing: shrink the observation's pull toward "known".
    if hints_used and observed > p:
        observed = p + (observed - p) / (1 + hints_used)
    learned = observed + (1 - observed) * params.p_learn
    w = min(max(concept_weight, 0.0), 1.0)
    return round(p + w * (learned - p), 6)


def confidence(attempts: int) -> float:
    """How much evidence backs the estimate (0 none → approaches 1)."""
    return round(1 - 1 / (1 + 0.35 * attempts), 4)


def level(p_known: float | None, attempts: int) -> str:
    if p_known is None or attempts == 0:
        return "not_started"
    if p_known >= MASTERED_AT and attempts >= MASTERED_MIN_ATTEMPTS:
        return "mastered"
    if p_known < WEAK_BELOW:
        return "weak"
    if p_known < DEVELOPING_BELOW:
        return "developing"
    return "proficient"
