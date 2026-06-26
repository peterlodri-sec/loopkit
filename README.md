# 🔁 LoopKit — Your Loop Engineering Starter Kit

> Build self-improving systems. The same pattern that produced 15 kompress models,
> now in a box you can clone and extend.

```bash
git clone https://github.com/peterlodri-sec/loopkit
cd loopkit
python -m loops.hello.loop
# 5 iterations. SHIP. You just ran your first loop.
```

[▶️ Open in Colab](https://colab.research.google.com/github/peterlodri-sec/loopkit/blob/main/notebooks/loopkit_hello.ipynb)

---

## What can you build with this?

| You want to... | Use this |
|---|---|
| Fine-tune a model iteratively | `loops/template/` → implement plan/execute/evaluate/decide |
| Have a bot run experiments for you | `bot/main.py` — Telegram bot with council |
| Understand loop engineering | `GUIDE.md` — tiered guide with patterns |
| See a real example | `loops/kompress/` — the full 15-model pipeline |
| Run in a notebook | `notebooks/loopkit_hello.ipynb` — Colab-ready |
| Teach someone the concept | `concepts/` — self-labeling, evaluator-optimizer, council |
| Run a daily repo health check | `loops/daily_triage/` — CI, issues, stale branches, outdated deps |
| Add quality gates to any loop | `loops/verification/` — LangChain Level 2: grader checks, retries on failure |
| Test if compression breaks agents | `loops/headroom_swebench/` — SWE-bench style: compare with/without compression |
| Run CI safety gates for headroom | `evals/headroom_swebench.py` — exit 0=pass, 1=regression |

---

## The Loop Pattern

Every loop has four phases:

```
  plan ──→ execute ──→ evaluate ──→ decide
    ↑                                   │
    └───────────────────────────────────┘
```

| Phase | Question | Example (kompress v8) |
|---|---|---|
| **plan** | What should we try? | "Use Qwen2.5-7B as teacher" |
| **execute** | Run the experiment | Label 97 texts → train 3 epochs on RTX 4090 |
| **evaluate** | How did it do? | Heretic exact: 0.955, agent mk_in_ref: 1.000 |
| **decide** | What next? | Council: SHIP — best model yet |

---

## Get a Telegram Bot Running (5 min)

```bash
# 1. Create a bot with @BotFather on Telegram → get token
# 2. Install
pip install python-telegram-bot huggingface_hub

# 3. Run
export LOOPKIT_BOT_TOKEN="your_token"
python -m bot.main

# 4. Chat with your bot on Telegram:
#    /new my-experiment
#    /run my-experiment
#    /decide my-experiment
```

Your bot will:
- Remember experiments across restarts (SQLite)
- Use the council (LLM) to review results and suggest next steps
- Fall back to heuristic rules if no LLM is available

---

## Real Results: The Kompress Loop

This kit was extracted from a real loop that produced 15 models:

| Version | Heretic | Keep | Lesson |
|---|---|---|---|
| v2 | 0.975 | 90% | Precision ceiling |
| v4 | 0.943 | 82% | Override internalized |
| **v8** | **0.955** | **85%** | **Production — Qwen teacher + C3** |
| v11 | 0.906 | 52% | Larger encoder ≠ better |
| v14 | 0.882 | — | Council concept proven |

📖 [Full story on vaked.dev](https://pocoo.vaked.dev/posts/2026-06-25-kompress-heretic-eval)
🤗 [All models on HuggingFace](https://huggingface.co/PeetPedro)
🔧 [Training repo](https://github.com/peterlodri-sec/ultrawhale)

---

## Structure

```
loopkit/
├── GUIDE.md              ← The full guide
├── README.md             ← You are here
├── bot/                  ← Telegram bot (outer loop)
│   ├── main.py           ← Entry point
│   ├── memory.py         ← SQLite persistence
│   └── council.py        ← LLM decision maker
├── loops/                ← Loop implementations
│   ├── base.py           ← Abstract Loop class
│   ├── hello/            ← Minimal example (start here!)
│   ├── template/         ← Copy this for new loops
│   ├── daily_triage/     ← Morning routine — CI, issues, deps
│   ├── verification/     ← LangChain L2 — grader + retry
│   ├── headroom_swebench/ ← Does compression break agents?
│   └── kompress/         ← Full kompress pipeline
├── concepts/             ← Reference patterns
│   ├── self_labeling.py
│   ├── evaluator_optimizer.py
│   └── council.py
├── evals/                ← Shared evaluation tools
│   └── heretic.py
└── notebooks/            ← Colab-ready notebooks
    └── loopkit_hello.ipynb
```

---

## The Loop Engineering Ecosystem

LoopKit is part of a growing movement. Here's the full picture:

| Resource | What it offers |
|---|---|
| **[Addy Osmani: Loop Engineering](https://addyosmani.com/blog/loop-engineering/)** | The canonical essay — 5 building blocks + memory, practical patterns, warnings |
| **[Cobus Greyling: loop-engineering](https://github.com/cobusgreyling/loop-engineering)** | Reference implementation with npm tools (loop-audit, loop-init, loop-cost), 7 patterns, pattern picker, goal engineering |
| **[LangChain: The Art of Loop Engineering](https://www.langchain.com/blog/the-art-of-loop-engineering)** | 4 stacked loops (Agent → Verification → Event-Driven → Hill Climbing), "loopcraft" concept |
| **LoopKit (this repo)** | Python-native starter kit with Telegram bot, council, Colab notebook, kompress case study |

### Key concepts from the ecosystem

**From Addy Osmani** — the 5 building blocks + memory:
- **Automations**: Scheduled discovery & triage on a cadence
- **Worktrees**: Safe parallel execution on isolated branches
- **Skills**: Persistent project knowledge (`SKILL.md`)
- **Plugins & Connectors**: MCP-based tools that reach into your stack
- **Sub-agents**: Maker/checker split — the model that wrote code is too nice grading its own work
- **Memory**: A markdown file outside conversation context — "the agent forgets, the repo does not"

**From LangChain** — the 4 stacked loops:
1. **Agent Loop**: Model calls tools until done
2. **Verification Loop**: Grader checks output, retries if needed
3. **Event-Driven Loop**: Webhooks/cron trigger agents automatically
4. **Hill Climbing Loop**: Analysis agent reviews traces, rewrites the harness — *the loop that improves the loop*

**From Cobus Greyling** — production tools:
- `loop-audit` — scores your loop's readiness
- `loop-init` — scaffolds new loops from patterns
- `loop-cost` — estimates token spend before you run
- 7 battle-tested patterns with real win/failure stories

### How LoopKit fits

LoopKit implements the **Agent Loop** (level 1) and **Verification Loop** (level 2) in Python,
with the **Hill Climbing Loop** (level 4) via the Council. The **Event-Driven Loop** (level 3)
is the Telegram bot. Combine with [cobusgreyling/loop-engineering](https://github.com/cobusgreyling/loop-engineering)
for the full stack.

---

## Further Reading

- 📄 Anthropic: Engineering Groups of AI Agents (June 2025)
- 📝 [The kompress heretic eval — full loop story](https://pocoo.vaked.dev/posts/2026-06-25-kompress-heretic-eval)
- 🔧 [Headroom — the proxy that uses kompress](https://github.com/headroomlabs-ai/headroom)
- 🧪 [Heretic — adversarial ablation testing](https://github.com/p-e-w/heretic)

---

MIT License. Build loops. Ship models.


---

📝 [Blog post: Introducing LoopKit](https://pocoo.vaked.dev/posts/2026-06-25-loopkit)