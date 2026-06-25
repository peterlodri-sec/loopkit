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

---

## Advanced: Dogfooding LoopKit — The Ralph Loop

> *"Don't just build the loop — run yourself through it."*

The ultimate test of any self-improving system is to turn it on itself. This
section walks through adding **observability** (OpenTelemetry) and **dataset
collection** (HuggingFace datasets) to LoopKit, making the loop itself observable
and the data it produces shareable. We call this the **Ralph Loop** — the loop
that watches the loop.

### Step 1: Add OpenTelemetry — make every loop iteration observable

```bash
pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp
```

Add to `loops/base.py`:

```python
# At the top of loops/base.py
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider

# Initialize once
trace.set_tracer_provider(TracerProvider())
metrics.set_meter_provider(MeterProvider())
tracer = trace.get_tracer("loopkit")
meter = metrics.get_meter("loopkit")

# Counters for the loop
iteration_counter = meter.create_counter("loop.iterations")
decision_counter = meter.create_counter("loop.decisions")
duration_histogram = meter.create_histogram("loop.iteration_duration_seconds")
```

Then instrument the `run()` method:

```python
def run(self, context: dict | None = None) -> Experiment:
    with tracer.start_as_current_span(f"{self.name}.run") as span:
        span.set_attribute("loop.name", self.name)
        span.set_attribute("loop.iteration", len(self.history) + 1)
        
        t0 = time.perf_counter()
        
        # ... existing plan/execute/evaluate/decide logic ...
        
        duration = time.perf_counter() - t0
        duration_histogram.record(duration, {"loop": self.name})
        iteration_counter.add(1, {"loop": self.name})
        decision_counter.add(1, {"loop": self.name, "decision": exp.decision.value})
        
        span.set_attribute("decision", exp.decision.value)
        return exp
```

Now every loop iteration emits traces and metrics. Export to Jaeger, Prometheus,
or any OTLP-compatible backend. You can see: which loops are running, how long
each iteration takes, what decisions are being made, and where time is spent.

### Step 2: Dataset Collection — every experiment produces a dataset

```bash
pip install datasets
```

Add to `loops/base.py`:

```python
from datasets import Dataset
import pandas as pd

class Loop(abc.ABC):
    # ... existing code ...
    
    def export_dataset(self) -> Dataset:
        """Export all experiment history as a HuggingFace Dataset."""
        rows = []
        for exp in self.history:
            row = {
                "id": exp.id,
                "loop": self.name,
                "decision": exp.decision.value if exp.decision else None,
                "reasoning": exp.reasoning,
                "started_at": exp.started_at,
                "completed_at": exp.completed_at,
            }
            # Flatten plan and results into top-level columns
            for k, v in exp.plan.items():
                row[f"plan_{k}"] = str(v)
            for k, v in exp.results.items():
                row[f"result_{k}"] = v if isinstance(v, (int, float, str, bool)) else str(v)
            rows.append(row)
        
        ds = Dataset.from_pandas(pd.DataFrame(rows))
        return ds
    
    def push_dataset(self, repo_id: str, token: str | None = None):
        """Push loop history to HuggingFace datasets."""
        ds = self.export_dataset()
        ds.push_to_hub(repo_id, token=token)
```

Now any loop can export its entire history as a dataset:

```python
loop = MyLoop("experiment-42")
loop.run_until(Decision.SHIP)
loop.push_dataset("peterlodri-sec/experiment-42-history")
# → huggingface.co/datasets/peterlodri-sec/experiment-42-history
```

### Step 3: The Ralph Loop — loop watching the loop

Now create a meta-loop that monitors ALL loops:

```python
class RalphLoop(Loop):
    """The loop that watches the loop."""
    
    def __init__(self):
        super().__init__("ralph")
        self.watched_loops: dict[str, Loop] = {}
    
    def watch(self, name: str, loop: Loop):
        self.watched_loops[name] = loop
    
    def plan(self, context):
        # Check all watched loops for anomalies
        alerts = []
        for name, loop in self.watched_loops.items():
            if not loop.history:
                continue
            last = loop.history[-1]
            if last.decision == Decision.PIVOT and len(loop.history) > 3:
                alerts.append(f"{name}: pivoting after {len(loop.history)} iterations")
            if last.decision == Decision.RETRAIN and len(loop.history) > 8:
                alerts.append(f"{name}: retraining >8 iterations — maybe give up?")
        
        return {"alerts": alerts, "watched_count": len(self.watched_loops)}
    
    def execute(self, plan):
        # Push all watched loop datasets to HF
        for name, loop in self.watched_loops.items():
            loop.push_dataset(f"peterlodri-sec/{name}-history")
        return {"pushed": len(self.watched_loops), "alerts": plan["alerts"]}
    
    def evaluate(self, results):
        has_alerts = len(results["alerts"]) > 0
        return {"healthy": not has_alerts, "alerts": results["alerts"]}
    
    def decide(self, metrics, history):
        if metrics["healthy"]:
            return Decision.CONTINUE, "All loops healthy"
        return Decision.CONTINUE, f"Alerts: {metrics['alerts']}"

# Run Ralph as a background watcher
ralph = RalphLoop()
ralph.watch("kompress-v15", kompress_loop)
ralph.watch("my-experiment", my_loop)
ralph.run_until(Decision.SHIP, max_iterations=100)  # runs forever, watching
```

### Step 4: Connect the bot to Ralph

Add to `bot/main.py`:

```python
# In the bot, after each /run:
ralph.watch(name, loop)
# Ralph picks up the new experiment in its next iteration

# New command:
async def ralph_status(update, context):
    """Check what Ralph sees."""
    if not ralph.watched_loops:
        await update.message.reply_text("Ralph isn't watching any loops yet.")
        return
    lines = ["👁 **Ralph is watching:**\n", ""]
    for name, loop in ralph.watched_loops.items():
        s = loop.status()
        emoji = {"ship": "✅", "continue": "🔄", "retrain": "⚠️", "pivot": "🔀"}.get(
            s.get("last_decision", ""), "❓"
        )
        lines.append(f"{emoji} **{name}**: {s['iterations']} runs, last: {s['last_decision']}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

app.add_handler(CommandHandler("ralph", ralph_status))
```

### What you get with Ralph + OpenTelemetry + Datasets

| Capability | Tool | What it gives you |
|---|---|---|
| **Observability** | OpenTelemetry | Traces, metrics, dashboards — see every loop iteration live |
| **Reproducibility** | HuggingFace Datasets | Every experiment's plan, results, and decision is a queryable dataset |
| **Monitoring** | Ralph Loop | A loop watching other loops — alerts on stalls, pivots, overfitting |
| **Sharing** | HF Datasets | Anyone can load your experiment history: `load_dataset("peterlodri-sec/kompress-v15-history")` |
| **Debugging** | OTLP traces | See exactly where time is spent in each phase |

### The full picture

```
                    ┌─────────────────────────────┐
                    │      Ralph Loop             │
                    │  (watches all loops)        │
                    │  • Alerts on stalls         │
                    │  • Pushes HF datasets       │
                    │  • OpenTelemetry metrics    │
                    └──────────┬──────────────────┘
                               │ watches
            ┌──────────────────┼──────────────────┐
            ▼                  ▼                  ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │ kompress-v15 │  │ my-experiment│  │  trading-bot │
    │  plan→exec   │  │  plan→exec   │  │  plan→exec   │
    │  eval→decide │  │  eval→decide │  │  eval→decide │
    └──────────────┘  └──────────────┘  └──────────────┘
            │                  │                  │
            ▼                  ▼                  ▼
    ┌──────────────────────────────────────────────────┐
    │              HuggingFace Datasets                │
    │  peterlodri-sec/kompress-v15-history             │
    │  peterlodri-sec/my-experiment-history            │
    │  peterlodri-sec/trading-bot-history              │
    └──────────────────────────────────────────────────┘
```

This is the advanced setup. Start with the hello loop. Add the bot. Add Ralph when
you have multiple loops running. Add OpenTelemetry when you need to debug. The
system scales with your ambition.
