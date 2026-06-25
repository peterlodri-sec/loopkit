"""Hello Loop — minimal example. Counts iterations, stops at 5.

The simplest possible loop:
  plan: "count to N"
  execute: increment counter
  evaluate: is counter >= 5?
  decide: SHIP if >= 5, else CONTINUE

Run it:
  python -m loops.hello.loop
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loops.base import Loop, Decision


class HelloLoop(Loop):
    """Minimal loop: counts until it hits the target."""

    def __init__(self):
        super().__init__("hello")
        self.counter = len(self.history)

    def plan(self, context: dict) -> dict:
        target = context.get("target", 5)
        return {"action": "count", "target": target, "current": self.counter}

    def execute(self, plan: dict) -> dict:
        self.counter += 1
        return {"count": self.counter, "target": plan["target"]}

    def evaluate(self, results: dict) -> dict:
        reached = results["count"] >= results["target"]
        return {"reached_target": reached, "progress": f"{results['count']}/{results['target']}"}

    def decide(self, metrics: dict, history: list) -> tuple[Decision, str]:
        if metrics["reached_target"]:
            return Decision.SHIP, f"Reached target! ({metrics['progress']})"
        return Decision.CONTINUE, f"Keep counting... ({metrics['progress']})"


if __name__ == "__main__":
    loop = HelloLoop()
    runs = loop.run_until(Decision.SHIP, max_iterations=10)
    print(f"\nHello loop complete! {len(runs)} iterations.")
    for r in runs:
        print(f"  {r.id}: count={r.results['count']} → {r.decision.value} ({r.reasoning})")
