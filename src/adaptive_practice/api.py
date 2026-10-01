import os
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from adaptive_practice.exercises import BankGenerator, ExerciseGenerator, OpenAIExerciseGenerator
from adaptive_practice.models import Attempt, Exercise, Level, StudyPlan
from adaptive_practice.planner import build_plan
from adaptive_practice.store import EventStore


class AppendResult(BaseModel):
    inserted: bool


def create_app(
    store: EventStore | None = None, generator: ExerciseGenerator | None = None
) -> FastAPI:
    selected_store = store or EventStore(Path(os.environ.get("STUDY_DB", "data/study.db")))
    selected_generator = generator or (
        OpenAIExerciseGenerator()
        if os.environ.get("EXERCISE_PROVIDER") == "openai"
        else BankGenerator()
    )
    app = FastAPI(title="Adaptive Practice Engine", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/attempts", response_model=AppendResult)
    def append_attempt(attempt: Attempt) -> AppendResult:
        try:
            return AppendResult(inserted=selected_store.append(attempt))
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/v1/learners/{learner_id}/plan", response_model=StudyPlan)
    def plan(learner_id: str, at: datetime | None = None) -> StudyPlan:
        try:
            return build_plan(
                learner_id,
                selected_store.for_learner(learner_id),
                at or datetime.now(UTC),
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/v1/learners/{learner_id}/exercise", response_model=Exercise)
    def exercise(
        learner_id: str, level: Level = "A2", at: datetime | None = None
    ) -> Exercise:
        try:
            plan_result = build_plan(
                learner_id,
                selected_store.for_learner(learner_id),
                at or datetime.now(UTC),
            )
            return selected_generator.generate(plan_result.recommendations[0].skill, level)
        except ValueError as exc:
            raise HTTPException(status_code=502, detail="Exercise generation failed") from exc

    return app


app = create_app()

