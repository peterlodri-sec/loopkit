# Loop Engineering — The Guide

> *"The agent forgets. The repo does not." — Addy Osmani*

This guide explains **loop engineering**: the practice of building self-improving systems
that plan, execute, evaluate, and decide — over and over — until they converge on something
great. It's the pattern we used to train 15 kompress models. It's the pattern behind
every successful fine-tuning pipeline. And now it's yours.

---

## Quick Start (5 minutes)

```bash
git clone https://github.com/peterlodri-sec/loopkit
cd loopkit
pip install -e .

# Run the hello loop (5 iterations, automatically stops when target reached)
python -m loops.hello.loop
# Output: SHIP after 5 iterations. You just ran your first loop!

# Start your own
cp -r loops/template loops/my-project
# Edit loops/my-project/loop.py — implement plan(), execute(), evaluate(), decide()
python -m loops.my-project.loop
```

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/peterlodri-sec/loopkit/blob/main/notebooks/loopkit_hello.ipynb)

---

## What is Loop Engineering?

A **loop** is any process that improves itself through repeated cycles of:

```
  plan ──→ execute ──→ evaluate ──→ decide
    ↑                                   │
    └───────────────────────────────────┘
```

**Inner loop** — the thing you're optimizing. Train a model, evaluate it, train again.

**Outer loop** — the decision about *what* to optimize. Which teacher? Which data? Which architecture? This is where the council lives.

### The kompress story (a loop engineering case study)

We started with a problem: kompress drops critical tokens (compiler flags, hex addresses,
file paths) because its training data labeled them as optional.

**Inner loop**: Fine-tune model → run heretic eval → measure must-keep survival
**Outer loop**: Try different teachers (self-labels, Qwen2.5, Qwen3-Coder, GLM, regex),
different data (domain, synthetic, GLM-generated), different architectures (base vs large)

| Version | What we tried | Heretic | Lesson |
|---|---|---|---|
| v2 | — | 0.975 | Precision ceiling |
| v4 | Self-labels | 0.943 | Override internalized |
| v6 | Agent-distribution | 0.962 | Dead end — more conservative |
| **v8** | **Qwen2.5 teacher** | **0.955** | **Sweet spot — ship it** |
| v9 | C3-only | 0.921 | Overfit — need diversity |
| v11 | Larger encoder | 0.906 | Capacity ≠ precision |
| v14 | Council training | 0.882 | Concept proven, needs work |

After 15 versions, we converged on v8 + must-keep override (PR #1419). The loop produced
a model that saves 15% tokens while preserving 100% of critical information.

**Every decision in that table was a loop iteration.** The outer loop was us —
a human + an AI agent — asking "what should we try next?" and "what did we learn?"

LoopKit automates this outer loop so you can scale it.

---

## Group Engineering

In June 2025, Anthropic published [Engineering Groups of AI Agents](https://www.anthropic.com/engineering/engineering-groups-of-ai-agents) —
a paper describing how multiple AI agents can collaborate in structured groups
to accomplish complex engineering tasks.

Loop engineering is the **temporal** version of group engineering. Instead of
multiple agents working in parallel, you have multiple *iterations* working in
sequence — each learning from the last.

| Group Engineering | Loop Engineering |
|---|---|
| Multiple agents collaborate | Multiple iterations build on each other |
| Coordinator delegates tasks | Council decides next experiment |
| Agents have specialized roles | Each loop iteration has a hypothesis |
| Results merge into a solution | Results converge toward a target |

The council (our `bot/council.py`) is like the coordinator — it reviews results
and decides what the group should do next. You can extend it with multiple
council members (a "parliament") that debate before deciding.

---

## Patterns

These are the building blocks. Mix and match them in your loops.

### 1. Self-Labeling
The model labels its own training data. Run model on text → keep tokens with
high confidence → use those as labels for the next training run.

**When to use**: You have unlabeled data and a decent starting model.
**Risk**: Label noise compounds (v4→v5 regressed because of this).
**Implementation**: `concepts/self_labeling.py`

### 2. Evaluator-Optimizer
A stronger "teacher" model reviews the student's output and corrects mistakes.
Teacher labels must-keep tokens → train student to match teacher.

**When to use**: You have access to a stronger model (Qwen2.5, GLM, Claude).
**Risk**: Teacher bias (Qwen3-Coder preserved too many tokens → v12 regressed).
**Implementation**: `concepts/evaluator_optimizer.py`

### 3. C3 Self-Distillation
Collect real-world data, label with a teacher, train a smaller model to match.
"Collect → Curate → Compress" — hence C3.

**When to use**: Your training data distribution doesn't match production.
**Risk**: Small C3 datasets overfit (v9). Mix with generic data (v8: 33% C3).
**Implementation**: `loops/kompress/` — full example

### 4. Council
An LLM reviews experiment results and decides what to try next. Replaces the
human in the outer loop for faster iteration.

**When to use**: You have many experiments to run and clear evaluation metrics.
**Risk**: Council may ship too early or retrain indefinitely. Add guardrails.
**Implementation**: `bot/council.py`, `concepts/council.py`

### 5. The Loop Pattern (combine them all)
```
1. Self-label some data with your current model
2. Evaluator-optimizer: teacher corrects the worst labels
3. C3: mix teacher-labeled data with generic data
4. Train a new model
5. Council reviews: ship, retrain, or pivot?
6. Repeat
```

---

## Building Your Own Loop

### Minimal example (30 lines)

```python
from loops.base import Loop, Decision

class MyLoop(Loop):
    def plan(self, ctx): return {"lr": ctx.get("lr", 0.001)}
    def execute(self, plan): return {"loss": 1.0 - plan["lr"] * 10}  # fake training
    def evaluate(self, results): return {"good": results["loss"] < 0.5}
    def decide(self, metrics, history):
        if metrics["good"]: return Decision.SHIP, "Loss is low enough!"
        return Decision.CONTINUE, "Need lower loss"

loop = MyLoop("my-loop")
loop.run_until(Decision.SHIP, max_iterations=20)
```

### Template
Copy `loops/template/` and implement the four methods. The template includes:
- A placeholder Loop subclass
- Example state persistence
- Docstrings explaining each phase
- A `__main__` block for standalone execution

---

## Reference

- **[Anthropic: Engineering Groups of AI Agents](https://www.anthropic.com/engineering/engineering-groups-of-ai-agents)** — June 2025
- **[The kompress heretic benchmark](https://pocoo.vaked.dev/posts/2026-06-25-kompress-heretic-eval)** — full story of the 15-model loop
- **[All kompress models on HuggingFace](https://huggingface.co/PeetPedro)** — model cards with benchmarks
- **[Ultrawhale training repo](https://github.com/peterlodri-sec/ultrawhale)** — the loop that produced these models
- **[Headroom](https://github.com/headroomlabs-ai/headroom)** — the proxy that uses kompress
- **[Heretic](https://github.com/p-e-w/heretic)** — adversarial ablation testing (inspired our eval)

---

## FAQ

**Q: Do I need a GPU?**
A: For the hello loop, no. For real model training, yes — but you can use vast.ai (~$0.20/hr) or Colab's free GPU.

**Q: Can I use this without Telegram?**
A: Yes! The loop classes work standalone. The bot is optional — run loops directly with `python -m loops.yourloop.loop`.

**Q: How is this different from AutoML?**
A: AutoML searches hyperparameters. Loop engineering searches *ideas* — which teacher, which data, which architecture, which approach. The council makes qualitative decisions, not just numeric optimization.

**Q: What's the difference between a loop and a CI pipeline?**
A: A CI pipeline runs fixed tests on every commit. A loop *changes what it does* based on results. CI says "pass/fail." A loop says "what should we try next?"
