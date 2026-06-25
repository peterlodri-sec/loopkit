"""Verification Loop — LangChain Level 2: grader checks, retries on failure.

Pattern: Run an agent loop → grade the output against a rubric →
if it fails, give feedback and retry. Stops after max attempts.

Run it:
  python -m loops.verification.loop
"""

import sys, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loops.base import Loop, Decision


class VerificationLoop(Loop):
    """Wraps any loop with a grader that checks output quality."""

    def __init__(self, inner_loop: Loop, max_retries: int = 3):
        super().__init__("verification")
        self.inner = inner_loop
        self.max_retries = max_retries
        self.retries = 0

    def plan(self, context: dict) -> dict:
        return {"inner_loop": self.inner.name, "retry": self.retries, "max": self.max_retries}

    def execute(self, plan: dict) -> dict:
        # Run the inner loop
        exp = self.inner.run()
        # Simulate grading (in real use: LLM grades against rubric)
        grade = self._grade(exp.results)
        return {
            "inner_result": exp.results,
            "inner_decision": exp.decision.value if exp.decision else "?",
            "grade": grade,
            "retry_count": self.retries,
        }

    def evaluate(self, results: dict) -> dict:
        passed = results["grade"]["score"] >= 0.7
        return {
            "passed": passed,
            "score": results["grade"]["score"],
            "feedback": results["grade"]["feedback"],
        }

    def decide(self, metrics: dict, history: list) -> tuple[Decision, str]:
        if metrics["passed"]:
            return Decision.SHIP, f"✅ Passed verification (score: {metrics['score']:.2f})"
        
        self.retries += 1
        if self.retries >= self.max_retries:
            return Decision.SHIP, f"⚠️ Max retries ({self.max_retries}) reached. Shipping with score {metrics['score']:.2f}"
        
        return Decision.RETRAIN, (
            f"❌ Failed verification (score: {metrics['score']:.2f}). "
            f"Feedback: {metrics['feedback']}. Retrying ({self.retries}/{self.max_retries})..."
        )

    def _grade(self, results: dict) -> dict:
        """Simulated grader. Replace with real LLM-based grading."""
        # In production: LLM compares output against rubric
        # For the template, we simulate with random scoring
        score = random.uniform(0.3, 1.0)
        if score < 0.5:
            feedback = "Output missing key sections. Add more detail."
        elif score < 0.7:
            feedback = "Good structure but needs better error handling."
        else:
            feedback = "Looks solid. Minor formatting improvements."
        return {"score": round(score, 2), "feedback": feedback}


if __name__ == "__main__":
    from loops.hello.loop import HelloLoop
    inner = HelloLoop()
    verifier = VerificationLoop(inner, max_retries=3)
    
    print("🔍 Verification Loop — LangChain Level 2\n")
    runs = verifier.run_until(Decision.SHIP, max_iterations=5)
    
    for r in runs:
        g = r.results.get("grade", {})
        print(f"  {r.id}: score={g.get('score', '?')} → {r.decision.value}")
        if r.decision == Decision.RETRAIN:
            print(f"    Feedback: {g.get('feedback', '')}")
    print(f"\n✅ Verified in {len(runs)} attempt(s)")
