from datetime import UTC, datetime, timedelta

from adaptive_practice.models import SKILLS, Attempt, PlanItem, Skill, StudyPlan

INTERVAL_DAYS = (1, 2, 4, 7, 14, 30)


def _state(skill: Skill, attempts: list[Attempt], now: datetime) -> PlanItem:
    history = [a for a in attempts if a.skill == skill and a.occurred_at <= now]
    if not history:
        return PlanItem(
            skill=skill,
            mastery=0.5,
            due_at=now,
            priority=0.5,
            reason="New skill: no practice history yet.",
        )

    correct_count = sum(a.correct for a in history)
    mastery = (1 + correct_count) / (2 + len(history))  # Beta(1, 1) smoothing.
    streak = 0
    for attempt in reversed(history):
        if not attempt.correct:
            break
        streak += 1
    days = INTERVAL_DAYS[min(streak, len(INTERVAL_DAYS) - 1)] if streak else 1
    due_at = history[-1].occurred_at + timedelta(days=days)
    overdue_days = max(0.0, (now - due_at).total_seconds() / 86400)
    priority = (1 - mastery) + min(overdue_days, 7) * 0.15
    reason = (
        f"Due for review; {len(history)} attempts, {streak} recent correct, "
        f"estimated mastery {mastery:.2f}."
    )
    return PlanItem(
        skill=skill,
        mastery=round(mastery, 3),
        due_at=due_at,
        priority=round(priority, 3),
        reason=reason,
    )


def build_plan(learner_id: str, attempts: list[Attempt], as_of: datetime) -> StudyPlan:
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of must include a timezone")
    now = as_of.astimezone(UTC)
    items = [_state(skill, attempts, now) for skill in SKILLS]
    due = [item for item in items if item.due_at <= now]
    if due:
        ordered = sorted(due, key=lambda item: (-item.priority, item.skill))
    else:
        ordered = sorted(items, key=lambda item: (item.due_at, item.skill))
    return StudyPlan(learner_id=learner_id, as_of=now, recommendations=ordered[:3])

