"""The Loop — abstract base for any self-improving process.

A Loop has four phases:
  plan()    — decide what experiment to run next
  execute() — run the experiment (train, generate, evaluate)
  evaluate()— measure results against targets
  decide()  — interpret results, choose next action

This is the same pattern we used for kompress fine-tuning:
  plan: "try Qwen2.5-7B as teacher"
  execute: label 120 texts, train 3 epochs on vast.ai
  evaluate: heretic benchmark, agent mk_in_ref
  decide: "0.955 — ship it" or "0.921 — try something else"

To create your own loop, subclass Loop and implement the four phases.
See loops/hello/ for a minimal example, loops/kompress/ for a full one.
"""

from __future__ import annotations

import abc
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class Decision(str, Enum):
    CONTINUE = "continue"    # Keep going, more to try
    SHIP = "ship"            # Done — this is good enough
    PIVOT = "pivot"          # Change direction entirely
    RETRAIN = "retrain"       # Same direction, different params


@dataclass
class Experiment:
    """One run through the loop."""
    id: str
    plan: dict[str, Any] = field(default_factory=dict)
    results: dict[str, Any] = field(default_factory=dict)
    decision: Decision | None = None
    reasoning: str = ""
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "plan": self.plan,
            "results": self.results,
            "decision": self.decision.value if self.decision else None,
            "reasoning": self.reasoning,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


class Loop(abc.ABC):
    """Abstract loop. Subclass and implement the four phases."""

    def __init__(self, name: str, state_dir: str | None = None):
        self.name = name
        self.state_dir = Path(state_dir or f".loopkit/{name}")
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.history: list[Experiment] = []
        self._load_state()

    # ── Subclass these ──────────────────────────────────────────────

    @abc.abstractmethod
    def plan(self, context: dict) -> dict:
        """Decide what to try next. Returns a plan dict (any shape you want)."""
        ...

    @abc.abstractmethod
    def execute(self, plan: dict) -> dict:
        """Run the experiment. Returns results dict."""
        ...

    @abc.abstractmethod
    def evaluate(self, results: dict) -> dict:
        """Measure results against targets. Returns metrics dict."""
        ...

    @abc.abstractmethod
    def decide(self, metrics: dict, history: list[Experiment]) -> tuple[Decision, str]:
        """Interpret results. Returns (decision, reasoning)."""
        ...

    # ── Built-in loop runner ────────────────────────────────────────

    def run(self, context: dict | None = None) -> Experiment:
        """Run one full iteration: plan → execute → evaluate → decide."""
        ctx = context or {}

        plan = self.plan(ctx)
        exp = Experiment(
            id=f"{self.name}-{len(self.history)+1:03d}",
            plan=plan,
        )

        results = self.execute(plan)
        exp.results = results

        metrics = self.evaluate(results)
        decision, reasoning = self.decide(metrics, self.history)

        exp.decision = decision
        exp.reasoning = reasoning
        exp.completed_at = datetime.now(timezone.utc).isoformat()

        self.history.append(exp)
        self._save_state()
        return exp

    def run_until(self, target_decision: Decision = Decision.SHIP, max_iterations: int = 10) -> list[Experiment]:
        """Run the loop until a target decision or max iterations."""
        runs = []
        for _ in range(max_iterations):
            exp = self.run()
            runs.append(exp)
            if exp.decision == target_decision:
                break
        return runs

    # ── State persistence ───────────────────────────────────────────

    def _save_state(self):
        state = {
            "name": self.name,
            "history": [e.to_dict() for e in self.history],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        (self.state_dir / "state.json").write_text(json.dumps(state, indent=2))

    def _load_state(self):
        path = self.state_dir / "state.json"
        if path.exists():
            state = json.loads(path.read_text())
            self.history = [
                Experiment(
                    id=e["id"],
                    plan=e.get("plan", {}),
                    results=e.get("results", {}),
                    decision=Decision(e["decision"]) if e.get("decision") else None,
                    reasoning=e.get("reasoning", ""),
                    started_at=e.get("started_at", ""),
                    completed_at=e.get("completed_at"),
                )
                for e in state.get("history", [])
            ]

    def status(self) -> dict:
        """Human-readable status."""
        return {
            "name": self.name,
            "iterations": len(self.history),
            "last_decision": self.history[-1].decision.value if self.history else "none",
            "last_reasoning": self.history[-1].reasoning[:200] if self.history else "",
        }
