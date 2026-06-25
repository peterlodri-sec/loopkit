"""Persistent memory for the loop engineering bot.

Stores loop state, experiment history, and decisions in SQLite.
Survives bot restarts — your loops keep running.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_DB = Path.home() / ".loopkit" / "memory.db"


class LoopMemory:
    """SQLite-backed persistent memory."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or str(DEFAULT_DB)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS loops (
                    name TEXT PRIMARY KEY,
                    template TEXT,
                    created_at TEXT,
                    state_json TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS experiments (
                    id TEXT PRIMARY KEY,
                    loop_name TEXT,
                    plan_json TEXT,
                    results_json TEXT,
                    decision TEXT,
                    reasoning TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    FOREIGN KEY (loop_name) REFERENCES loops(name)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT
                )
            """)
            conn.commit()

    def create_loop(self, name: str, template: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO loops (name, template, created_at, state_json) VALUES (?, ?, ?, ?)",
                (name, template, datetime.now(timezone.utc).isoformat(), "{}"),
            )
            conn.commit()

    def save_experiment(self, loop_name: str, experiment: dict):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO experiments
                   (id, loop_name, plan_json, results_json, decision, reasoning, started_at, completed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    experiment["id"],
                    loop_name,
                    json.dumps(experiment.get("plan", {})),
                    json.dumps(experiment.get("results", {})),
                    experiment.get("decision"),
                    experiment.get("reasoning", ""),
                    experiment.get("started_at"),
                    experiment.get("completed_at"),
                ),
            )
            conn.commit()

    def get_history(self, loop_name: str) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM experiments WHERE loop_name = ? ORDER BY started_at",
                (loop_name,),
            ).fetchall()
        return [
            {
                "id": r[0], "loop_name": r[1],
                "plan": json.loads(r[2]), "results": json.loads(r[3]),
                "decision": r[4], "reasoning": r[5],
                "started_at": r[6], "completed_at": r[7],
            }
            for r in rows
        ]

    def remember(self, key: str, value: Any):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO memories (key, value, updated_at) VALUES (?, ?, ?)",
                (key, json.dumps(value), datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()

    def recall(self, key: str) -> Any | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT value FROM memories WHERE key = ?", (key,)
            ).fetchone()
        return json.loads(row[0]) if row else None


if __name__ == "__main__":
    # Quick test
    m = LoopMemory()
    m.create_loop("test", "hello")
    m.save_experiment("test", {
        "id": "test-001", "plan": {}, "results": {"score": 0.95},
        "decision": "ship", "reasoning": "great!", "started_at": "", "completed_at": "",
    })
    print("History:", m.get_history("test"))
    print("Memory OK")
