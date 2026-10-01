import json
import os
from typing import Protocol

from adaptive_practice.models import Exercise, Level, Skill


class ExerciseGenerator(Protocol):
    def generate(self, skill: Skill, level: Level) -> Exercise: ...


BANK: dict[Skill, tuple[str, str, str]] = {
    "articles": (
        "Fill the blank: I booked ___ apartment near the station.",
        "an",
        "Use 'an' before the vowel sound in 'apartment'.",
    ),
    "subject_verb": (
        "Fill the blank: She ___ English every Tuesday. (study)",
        "studies",
        "For she in the present simple, change study to studies.",
    ),
    "past_tense": (
        "Fill the blank: Yesterday we ___ to the museum. (go)",
        "went",
        "The past tense of go is went.",
    ),
    "travel_vocabulary": (
        "What word means the place where you check in for a flight?",
        "airport",
        "An airport is where passengers check in for flights.",
    ),
}


class BankGenerator:
    def generate(self, skill: Skill, level: Level) -> Exercise:
        prompt, answer, explanation = BANK[skill]
        return Exercise(
            skill=skill,
            level=level,
            prompt=prompt,
            expected_answer=answer,
            explanation=explanation,
            provider="bank",
        )


SCHEMA = {
    "type": "object",
    "properties": {
        "prompt": {"type": "string"},
        "expected_answer": {"type": "string"},
        "explanation": {"type": "string"},
    },
    "required": ["prompt", "expected_answer", "explanation"],
    "additionalProperties": False,
}


class OpenAIExerciseGenerator:
    """Optional constrained exercise generation; never receives learner identifiers or history."""

    def __init__(self, client: object | None = None, model: str | None = None) -> None:
        if client is None:
            from openai import OpenAI

            client = OpenAI()
        self.client = client
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")

    def generate(self, skill: Skill, level: Level) -> Exercise:
        response = self.client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "developer",
                    "content": (
                        "Create one short, age-neutral English practice exercise. "
                        "Use only the requested grammar or vocabulary skill. "
                        "Provide one unambiguous expected answer and a concise explanation. "
                        "No personal data, external links, or unsafe content."
                    ),
                },
                {"role": "user", "content": f"Skill: {skill}; CEFR level: {level}"},
            ],
            text={"format": {"type": "json_schema", "name": "practice_exercise", "schema": SCHEMA, "strict": True}},
        )
        if not response.output_text:
            raise ValueError("model returned no exercise")
        return Exercise.model_validate(
            {**json.loads(response.output_text), "skill": skill, "level": level, "provider": "openai"}
        )

