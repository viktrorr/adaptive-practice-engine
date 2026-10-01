from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from adaptive_practice.api import create_app
from adaptive_practice.eval import run_eval
from adaptive_practice.models import Attempt
from adaptive_practice.planner import build_plan
from adaptive_practice.store import EventStore


def event(event_id: str, learner: str, skill: str, correct: bool, when: str) -> Attempt:
    return Attempt(
        event_id=event_id,
        learner_id=learner,
        skill=skill,
        correct=correct,
        occurred_at=datetime.fromisoformat(when),
    )


def test_event_ingestion_is_idempotent_and_tenant_scoped(tmp_path: Path) -> None:
    store = EventStore(tmp_path / "events.db")
    attempt = event("event_1", "learner_a", "articles", False, "2026-10-01T12:00:00+00:00")
    assert store.append(attempt)
    assert not store.append(attempt)
    assert len(store.for_learner("learner_a")) == 1
    assert store.for_learner("learner_b") == []


def test_same_event_id_with_changed_payload_is_rejected(tmp_path: Path) -> None:
    client = TestClient(create_app(EventStore(tmp_path / "events.db")))
    body = {
        "event_id": "event_1",
        "learner_id": "learner_a",
        "skill": "articles",
        "correct": False,
        "occurred_at": "2026-10-01T12:00:00Z",
    }
    assert client.post("/v1/attempts", json=body).status_code == 200
    assert client.post("/v1/attempts", json={**body, "correct": True}).status_code == 409


def test_out_of_order_events_replay_deterministically(tmp_path: Path) -> None:
    store = EventStore(tmp_path / "events.db")
    late = event("event_2", "learner_a", "past_tense", True, "2026-10-02T12:00:00+00:00")
    early = event("event_1", "learner_a", "past_tense", False, "2026-10-01T12:00:00+00:00")
    store.append(late)
    store.append(early)
    assert [a.event_id for a in store.for_learner("learner_a")] == ["event_1", "event_2"]
    plan = build_plan("learner_a", store.for_learner("learner_a"), datetime(2026, 10, 5, tzinfo=UTC))
    assert plan.recommendations[0].skill == "past_tense"


def test_api_returns_explainable_plan_and_exercise(tmp_path: Path) -> None:
    client = TestClient(create_app(EventStore(tmp_path / "events.db")))
    response = client.post(
        "/v1/attempts",
        json={
            "event_id": "event_1",
            "learner_id": "learner_a",
            "skill": "past_tense",
            "correct": False,
            "occurred_at": "2026-10-01T12:00:00Z",
        },
    )
    assert response.json() == {"inserted": True}
    plan = client.get("/v1/learners/learner_a/plan?at=2026-10-04T12:00:00Z")
    assert plan.status_code == 200
    assert plan.json()["recommendations"][0]["skill"] == "past_tense"
    assert "Due for review" in plan.json()["recommendations"][0]["reason"]
    exercise = client.get("/v1/learners/learner_a/exercise?at=2026-10-04T12:00:00Z")
    assert exercise.json()["skill"] == "past_tense"
    assert exercise.json()["provider"] == "bank"


def test_naive_timestamp_is_rejected(tmp_path: Path) -> None:
    client = TestClient(create_app(EventStore(tmp_path / "events.db")))
    response = client.post(
        "/v1/attempts",
        json={
            "event_id": "event_1",
            "learner_id": "learner_a",
            "skill": "articles",
            "correct": True,
            "occurred_at": "2026-10-01T12:00:00",
        },
    )
    assert response.status_code == 422


def test_offline_planning_eval() -> None:
    fixture = Path(__file__).resolve().parents[1] / "evals" / "planning_cases.json"
    assert run_eval(fixture) == {"cases": 3, "top_1_match": 1.0}

