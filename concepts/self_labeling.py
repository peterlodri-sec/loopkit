"""Self-Labeling: model labels its own training data.

Pattern: Run model on unlabeled text → keep tokens with high confidence →
use those as labels for the next training run.

Used in: kompress v3→v4 (internalized must-keep override behavior)
Risk: Label noise compounds across iterations (v4→v5 regressed)

See GUIDE.md for when to use and risks.
"""

# Reference only — see ultrawhale/scripts/train_kompress.py for full implementation
# Key pattern:
#   1. Run model on text → get per-token keep/drop probabilities
#   2. Keep tokens with probability > threshold
#   3. Use kept tokens as "reference" for next training run
#   4. Repeat until convergence or plateau
