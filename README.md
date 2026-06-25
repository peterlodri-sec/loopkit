# 🔁 LoopKit — Your Loop Engineering Starter Kit

> Build self-improving systems. The same pattern that produced 15 kompress models,
> now in a box you can clone and extend.

```bash
git clone https://github.com/peterlodri-sec/loopkit
cd loopkit
python -m loops.hello.loop
# 5 iterations. SHIP. You just ran your first loop.
```

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/peterlodri-sec/loopkit/blob/main/notebooks/loopkit_hello.ipynb)

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

## Further Reading

- 📄 Anthropic: Engineering Groups of AI Agents (June 2025) (June 2025)
- 📝 [The kompress heretic eval — full loop story](https://pocoo.vaked.dev/posts/2026-06-25-kompress-heretic-eval)
- 🔧 [Headroom — the proxy that uses kompress](https://github.com/headroomlabs-ai/headroom)
- 🧪 [Heretic — adversarial ablation testing](https://github.com/p-e-w/heretic)

---

MIT License. Build loops. Ship models.


---

📝 [Blog post: Introducing LoopKit](https://pocoo.vaked.dev/posts/2026-06-25-loopkit)