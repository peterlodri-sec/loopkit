"""Template Loop — copy me and implement the four phases.

Usage:
  cp -r loops/template loops/my-project
  # Edit loops/my-project/loop.py — implement plan/execute/evaluate/decide
  python -m loops.my-project.loop
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loops.base import Loop, Decision


class TemplateLoop(Loop):
    """Replace this docstring with what YOUR loop does."""

    def __init__(self):
        super().__init__("template")
        # Initialize your state here (models, counters, configs)

    def plan(self, context: dict) -> dict:
        """Decide what experiment to run next.

        Args:
            context: Optional context dict passed to loop.run(context={...})
        
        Returns:
            A plan dict — any shape you want. This is your experiment config.
        
        Example:
            return {"learning_rate": 0.001, "epochs": 3, "data": "v8_data.jsonl"}
        """
        # TODO: implement your planning logic
        return {"action": "experiment", "iteration": len(self.history) + 1}

    def execute(self, plan: dict) -> dict:
        """Run the experiment.

        This is where the actual work happens — train a model, generate data,
        run a simulation, whatever your loop does.
        
        Returns:
            Results dict — raw output of your experiment.
        
        Example:
            model = train(data=plan["data"], lr=plan["learning_rate"], epochs=plan["epochs"])
            return {"loss": model.final_loss, "accuracy": model.accuracy}
        """
        # TODO: implement your experiment
        iteration = plan.get("iteration", 1)
        return {"completed": True, "iteration": iteration}

    def evaluate(self, results: dict) -> dict:
        """Measure results against your targets.

        Returns:
            Metrics dict — numbers the council uses to decide.
        
        Example:
            return {"loss": results["loss"], "target_met": results["accuracy"] >= 0.95}
        """
        # TODO: implement your evaluation
        return {"success": results.get("completed", False)}

    def decide(self, metrics: dict, history: list) -> tuple[Decision, str]:
        """Interpret results and decide next action.

        Returns:
            (Decision, reasoning_string)
        
        Decision options:
            SHIP — results meet targets, stop the loop
            CONTINUE — keep going, more iterations needed
            RETRAIN — same direction, different parameters  
            PIVOT — change direction entirely
        """
        # TODO: implement your decision logic
        if metrics.get("success"):
            return Decision.SHIP, "Experiment completed successfully"
        return Decision.CONTINUE, "Keep iterating"


if __name__ == "__main__":
    loop = TemplateLoop()
    runs = loop.run_until(Decision.SHIP, max_iterations=5)
    print(f"\nTemplate loop complete! {len(runs)} iterations.")
    for r in runs:
        print(f"  {r.id}: {r.results} → {r.decision.value}")
