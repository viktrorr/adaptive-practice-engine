import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from adaptive_practice.models import Attempt


class EventStore:
    """Append-only attempts; replay order is event time then event ID."""

    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS attempts (
                    learner_id TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    skill TEXT NOT NULL,
                    correct INTEGER NOT NULL,
                    occurred_at TEXT NOT NULL,
                    PRIMARY KEY (learner_id, event_id)
                )"""
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS attempts_by_learner "
                "ON attempts (learner_id, occurred_at, event_id)"
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=5)
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def append(self, attempt: Attempt) -> bool:
        values = (
            attempt.learner_id,
            attempt.event_id,
            attempt.skill,
            int(attempt.correct),
            attempt.occurred_at.astimezone(UTC).isoformat(),
        )
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO attempts VALUES (?, ?, ?, ?, ?)",
                values,
            )
            if cursor.rowcount == 1:
                return True
            existing = conn.execute(
                "SELECT learner_id, event_id, skill, correct, occurred_at FROM attempts "
                "WHERE learner_id = ? AND event_id = ?",
                values[:2],
            ).fetchone()
            if existing != values:
                raise ValueError("event_id already exists with different content")
            return False

    def for_learner(self, learner_id: str) -> list[Attempt]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT event_id, skill, correct, occurred_at FROM attempts "
                "WHERE learner_id = ? ORDER BY occurred_at, event_id",
                (learner_id,),
            ).fetchall()
        return [
            Attempt(
                event_id=event_id,
                learner_id=learner_id,
                skill=skill,
                correct=bool(correct),
                occurred_at=datetime.fromisoformat(occurred_at),
            )
            for event_id, skill, correct, occurred_at in rows
        ]

