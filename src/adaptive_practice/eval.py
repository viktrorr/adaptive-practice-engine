import json
from datetime import datetime
from pathlib import Path

from adaptive_practice.models import Attempt
from adaptive_practice.planner import build_plan


def run_eval(path: Path) -> dict[str, float | int]:
    cases = json.loads(path.read_text(encoding="utf-8"))
    correct = 0
    for case in cases:
        attempts = [Attempt.model_validate(event) for event in case["events"]]
        plan = build_plan(case["learner_id"], attempts, datetime.fromisoformat(case["as_of"]))
        correct += plan.recommendations[0].skill == case["expected_top_skill"]
    return {"cases": len(cases), "top_1_match": round(correct / len(cases), 3)}


if __name__ == "__main__":
    fixture = Path(__file__).resolve().parents[2] / "evals" / "planning_cases.json"
    print(json.dumps(run_eval(fixture), indent=2))

