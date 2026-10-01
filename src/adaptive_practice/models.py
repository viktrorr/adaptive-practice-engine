from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Skill = Literal["articles", "subject_verb", "past_tense", "travel_vocabulary"]
SKILLS: tuple[Skill, ...] = ("articles", "subject_verb", "past_tense", "travel_vocabulary")
Level = Literal["A1", "A2", "B1", "B2"]


class Attempt(BaseModel):
    event_id: str = Field(min_length=4, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    learner_id: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    skill: Skill
    correct: bool
    occurred_at: datetime

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must include a timezone")
        return value


class PlanItem(BaseModel):
    skill: Skill
    mastery: float = Field(ge=0, le=1)
    due_at: datetime
    priority: float
    reason: str


class StudyPlan(BaseModel):
    learner_id: str
    as_of: datetime
    recommendations: list[PlanItem]


class Exercise(BaseModel):
    skill: Skill
    level: Level
    prompt: str = Field(min_length=8, max_length=400)
    expected_answer: str = Field(min_length=1, max_length=120)
    explanation: str = Field(min_length=8, max_length=300)
    provider: Literal["bank", "openai"]

