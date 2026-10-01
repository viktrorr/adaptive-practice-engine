# Adaptive Practice Engine

An independent AI software engineering portfolio project: an event-driven language-practice planner with durable SQLite storage, explainable recommendations, and optional LLM-generated exercises. It is **not affiliated with Preply**.

## Why this project

Learning products need more than a prompt. They need reliable events, deterministic state, an adaptive decision policy, meaningful metrics, and a clean boundary where generative AI can help. This project separates those concerns.

## Features

- Idempotent attempt ingestion, keyed by learner and event ID.
- UTC-normalized, append-only events and deterministic replay of out-of-order events.
- A transparent review policy combining smoothed mastery and spaced repetition.
- A local exercise bank that works offline; optional OpenAI Responses API generation with strict schema.
- A small synthetic evaluation set with expected top recommendations.

## Run locally

```bash
python -m venv .venv
# Activate the virtual environment for your shell, then:
python -m pip install -e '.[dev,llm]'
uvicorn adaptive_practice.api:app --reload
```

Open `http://127.0.0.1:8000/docs`, then record an event:

```bash
curl -X POST http://127.0.0.1:8000/v1/attempts \
  -H 'Content-Type: application/json' \
  -d '{"event_id":"demo_001","learner_id":"demo_learner","skill":"past_tense","correct":false,"occurred_at":"2026-10-01T12:00:00Z"}'
curl 'http://127.0.0.1:8000/v1/learners/demo_learner/plan?at=2026-10-04T12:00:00Z'
curl 'http://127.0.0.1:8000/v1/learners/demo_learner/exercise?at=2026-10-04T12:00:00Z'
```

By default exercise text comes from a checked-in synthetic bank. For live model generation, set `OPENAI_API_KEY`, optionally `OPENAI_MODEL`, and `EXERCISE_PROVIDER=openai`. The LLM receives only the selected skill and CEFR level, not learner IDs or event history. Model use may incur cost.

## Evaluate

```bash
pytest -q
python -m adaptive_practice.eval
ruff check .
```

The fixture reports top-1 agreement with three hand-authored expected recommendations. This is a **software regression check**, not a claim of learning gains. A real product would need educational research, consented learner data, A/B testing, and guardrails for age-appropriate content.

## Decision policy

For each skill, the planner replays events in event-time order, estimates mastery with a Beta(1,1) prior, schedules the next review from the current correct streak, and prioritizes weak overdue skills. A new skill is immediately eligible. The API returns the reason and due time, so the recommendation is inspectable.

## Production boundary

This is a local demo, not an authenticated multi-tenant service. Before public deployment, add identity and authorization, migrations, rate limits, observability, data retention controls, and stronger exercise validation. Runtime databases and credentials are ignored by Git.

## License

MIT. Synthetic content only; no user or Preply data.

