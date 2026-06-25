"""Council: LLM reviews experiment results and decides next action.

Pattern: After each loop iteration, feed results + history to an LLM →
LLM decides: SHIP (good enough), RETRAIN (same direction), PIVOT (change),
or CONTINUE (more iterations).

Used in: kompress v14 (GLM-5.1 council — concept proven)
Risk: Council may ship too early or retrain indefinitely

See GUIDE.md for when to use and risks.
"""

# Reference — full implementation in bot/council.py
# Key pattern:
#   1. Collect results + history from loop
#   2. Prompt LLM: "Here's what we tried, here are the results, what next?"
#   3. Parse decision: SHIP / RETRAIN / PIVOT / CONTINUE
#   4. Apply decision to loop control flow
#   5. Council can also suggest specific changes (LR, data, architecture)
