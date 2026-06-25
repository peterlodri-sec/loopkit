"""Evaluator-Optimizer: stronger teacher corrects student's mistakes.

Pattern: Teacher model (e.g., Qwen2.5-7B, GLM-5.2, Claude) reviews student
output → identifies must-keep tokens the student missed → creates corrected
labels → train student on corrected labels.

Used in: kompress v8 (Qwen2.5 teacher → 0.955), v12 (Qwen3-Coder → 0.949)
Risk: Teacher bias — Qwen3-Coder preserved too many tokens

See GUIDE.md for when to use and risks.
"""

# Reference only — see ultrawhale/scripts/evaluator_optimizer.py for full implementation
# Key pattern:
#   1. Run student model on text → get compression
#   2. Ask teacher to identify must-keep spans
#   3. Compare student output vs teacher labels
#   4. Train student on teacher labels for pairs where student failed
#   5. Repeat
