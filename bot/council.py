"""Council — an LLM that reviews loop results and suggests next actions.

The council is the "outer loop" decision-maker. It reviews experiment
results and decides: ship, retrain, pivot, or continue.

Uses any LLM available: GLM-5.1 (free HF inference), Claude, GPT-4, etc.
Falls back to heuristic rules if no LLM is available.
"""

import json
import os
from typing import Any


class Council:
    """LLM-powered decision maker for loop experiments."""

    def __init__(self, model: str | None = None):
        self.model = model or os.environ.get("COUNCIL_MODEL", "zai-org/GLM-5.1-FP8")

    def review(
        self,
        loop_name: str,
        results: dict[str, Any],
        history: list[dict],
    ) -> tuple[str, str]:
        """Review results and return (decision, reasoning)."""
        
        # Try LLM first
        try:
            return self._llm_review(loop_name, results, history)
        except Exception:
            pass
        
        # Fallback: heuristic rules
        return self._heuristic_review(loop_name, results, history)

    def _llm_review(self, loop_name: str, results: dict, history: list[dict]) -> tuple[str, str]:
        """Use an LLM to review results."""
        from huggingface_hub import InferenceClient

        token = os.environ.get("HF_TOKEN") or os.environ.get("HF_INFER_PRO", "")
        if not token:
            raise RuntimeError("No HF token available")

        client = InferenceClient(token=token)

        # Build context
        history_str = ""
        for h in history[-5:]:
            history_str += f"- {h['id']}: {json.dumps(h.get('results', {}))[:100]} → {h.get('decision', '?')}\n"

        prompt = f"""You are reviewing an experiment loop called "{loop_name}".

Latest results: {json.dumps(results)[:500]}

Recent history:
{history_str}

Decide:
- SHIP: results meet targets, ready to deploy
- RETRAIN: same direction, different parameters
- CONTINUE: more iterations needed
- PIVOT: change direction entirely

Reply with ONLY: DECISION: <word>
REASONING: <one sentence>"""

        r = client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model=self.model,
            max_tokens=60,
            temperature=0.1,
        )
        response = r.choices[0].message.content
        return self._parse_response(response)

    def _heuristic_review(self, loop_name: str, results: dict, history: list[dict]) -> tuple[str, str]:
        """Simple heuristic rules when no LLM is available."""
        iterations = len(history) + 1
        
        # Check for score in results
        score = None
        for key in ["score", "heretic", "accuracy", "exact_pct", "exact_base"]:
            if key in results:
                score = results[key]
                break
            if isinstance(results.get("summary"), dict):
                score = results["summary"].get(key)

        if score is not None:
            if score >= 0.95:
                return "SHIP", f"Score {score:.3f} meets target (>= 0.95)"
            elif iterations >= 10:
                return "SHIP", f"Max iterations ({iterations}) reached at score {score:.3f}"
            elif iterations >= 5 and score < 0.80:
                return "PIVOT", f"Score {score:.3f} too low after {iterations} iterations — try different approach"
            else:
                return "CONTINUE", f"Score {score:.3f}, keep improving (iteration {iterations})"
        
        return "CONTINUE", f"No score metric found, continue experimenting (iteration {iterations})"

    def _parse_response(self, response: str) -> tuple[str, str]:
        """Parse LLM response into decision and reasoning."""
        decision = "CONTINUE"
        reasoning = response[:200]

        for line in response.split("\n"):
            line_upper = line.upper()
            if line_upper.startswith("DECISION:"):
                word = line.split(":", 1)[1].strip().upper()
                if word in ("SHIP", "RETRAIN", "CONTINUE", "PIVOT"):
                    decision = word
            elif line_upper.startswith("REASONING:"):
                reasoning = line.split(":", 1)[1].strip()

        return decision, reasoning


if __name__ == "__main__":
    c = Council()
    decision, reasoning = c.review(
        "test-loop",
        {"score": 0.92, "loss": 0.34},
        [{"id": "test-001", "results": {"score": 0.88}, "decision": "continue"}],
    )
    print(f"Council: {decision} — {reasoning}")
