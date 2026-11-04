"""Spaced-repetition scheduling (SM-2 style) driven by the student's own answers.

- A wrong answer resets the interval to 1 day (a "lapse").
- A right answer grows it: 1 → 3 days → previous × ease. Ease drifts up with success and
  down with lapses, within [1.3, 2.8].
- Retention is an *estimate* (exponential forgetting, ~90 % at the due date) for display.
"""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

MIN_EASE, MAX_EASE, START_EASE = 1.3, 2.8, 2.3


@dataclass
class Schedule:
    interval_days: float
    ease: float
    repetitions: int
    lapses: int
    due_at: datetime
    reason: str


def next_schedule(prev: Schedule | None, *, correct: bool, now: datetime) -> Schedule:
    ease = prev.ease if prev else START_EASE
    reps = prev.repetitions if prev else 0
    lapses = prev.lapses if prev else 0
    if not correct:
        interval, reps, lapses = 1.0, 0, lapses + 1
        ease = max(MIN_EASE, ease - 0.2)
        reason = "mistake"
    else:
        reps += 1
        if reps == 1:
            interval = 1.0
        elif reps == 2:
            interval = 3.0
        else:
            interval = round((prev.interval_days if prev else 3.0) * ease, 2)
        ease = min(MAX_EASE, ease + 0.05)
        reason = prev.reason if prev and prev.reason == "mistake" and reps < 3 else "review"
    interval = min(interval, 180.0)
    return Schedule(interval, round(ease, 3), reps, lapses, now + timedelta(days=interval), reason)


def retention_estimate(
    interval_days: float, last_reviewed_at: datetime | None, now: datetime
) -> float | None:
    if last_reviewed_at is None:
        return None
    elapsed = max((now - last_reviewed_at).total_seconds() / 86400, 0)
    return round(math.exp(math.log(0.9) * elapsed / max(interval_days, 0.5)), 3)
