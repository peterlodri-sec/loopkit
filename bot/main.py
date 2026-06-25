"""LoopKit Bot — your personal loop engineering assistant on Telegram.

Setup:
  1. pip install python-telegram-bot
  2. Create a bot with @BotFather on Telegram, get your token
  3. export LOOPKIT_BOT_TOKEN="your_token_here"
  4. python -m bot.main

Commands:
  /start    — Welcome and setup
  /new      — Create a new loop
  /run      — Run one iteration of a loop
  /status   — Check loop status
  /decide   — Ask the council to review and decide
  /history  — Show experiment history
  /loops    — List all active loops

Or just chat naturally — the bot understands loop engineering concepts.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loops.base import Loop, Experiment, Decision
from bot.memory import LoopMemory
from bot.council import Council

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Try importing python-telegram-bot ───────────────────────────────
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    log.warning("python-telegram-bot not installed. Run: pip install python-telegram-bot")


# ── Bot state ──────────────────────────────────────────────────────
memory = LoopMemory()
council = Council()
active_loops: dict[str, Loop] = {}


# ── Command handlers ────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message."""
    await update.message.reply_text(
        "👋 I'm your **Loop Engineering Assistant**.\n\n"
        "I help you run experiments, evaluate results, and decide what to try next — "
        "the same workflow that produced 15 kompress models.\n\n"
        "**Commands:**\n"
        "/new <name> — Create a new loop\n"
        "/run <name> — Run one iteration\n"
        "/status — Check all loops\n"
        "/decide <name> — Ask the council\n"
        "/history <name> — Experiment log\n"
        "/loops — List active loops\n\n"
        "Or just chat! Say something like \"my model regressed, what should I try?\"",
        parse_mode="Markdown",
    )


async def new_loop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create a new loop from a template."""
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /new <name>\nExample: /new my-experiment")
        return

    name = args[0]
    # For now, create a hello-style loop
    from loops.hello.loop import HelloLoop
    loop = HelloLoop()
    loop.name = name
    active_loops[name] = loop
    memory.create_loop(name, "hello")

    await update.message.reply_text(
        f"✅ Created loop **{name}** (hello template).\n\n"
        f"Run it: /run {name}\n"
        f"Customize it in loops/{name}/loop.py",
        parse_mode="Markdown",
    )


async def run_loop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Run one iteration of a loop."""
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /run <loop_name>")
        return

    name = args[0]
    loop = active_loops.get(name)
    if not loop:
        await update.message.reply_text(f"❌ No loop named '{name}'. Create one with /new {name}")
        return

    await update.message.reply_text(f"🔄 Running **{name}**...", parse_mode="Markdown")
    
    try:
        exp = loop.run()
        await update.message.reply_text(
            f"✅ **{exp.id}** complete\n"
            f"Results: {json.dumps(exp.results, indent=2)[:500]}\n"
            f"Decision: **{exp.decision.value.upper()}**\n"
            f"Reasoning: {exp.reasoning}",
            parse_mode="Markdown",
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show status of all loops."""
    if not active_loops:
        await update.message.reply_text("No active loops. Create one with /new <name>")
        return

    lines = ["📊 **Loop Status**\n", ""]
    for name, loop in active_loops.items():
        s = loop.status()
        lines.append(f"**{name}**: {s['iterations']} runs, last: {s['last_decision']}")
        if s['last_reasoning']:
            lines.append(f"  _{s['last_reasoning'][:100]}_")
        lines.append("")
    
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def decide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask the council to review a loop and decide next steps."""
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /decide <loop_name>")
        return

    name = args[0]
    loop = active_loops.get(name)
    if not loop:
        await update.message.reply_text(f"❌ No loop named '{name}'")
        return

    if not loop.history:
        await update.message.reply_text(f"No experiments yet for {name}. Run one with /run {name}")
        return

    await update.message.reply_text(f"🧠 Council reviewing **{name}**...", parse_mode="Markdown")
    
    last = loop.history[-1]
    decision, reasoning = council.review(
        loop_name=name,
        results=last.results,
        history=[e.to_dict() for e in loop.history],
    )
    
    await update.message.reply_text(
        f"🏛 **Council Decision**: {decision.upper()}\n\n{reasoning}",
        parse_mode="Markdown",
    )


async def list_loops(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all active loops."""
    if not active_loops:
        await update.message.reply_text("No active loops. Create one with /new <name>")
        return

    lines = ["🔁 **Active Loops**\n", ""]
    for name, loop in active_loops.items():
        lines.append(f"• **{name}** — {len(loop.history)} experiments")
    lines.append(f"\n_{len(active_loops)} total_")
    
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show experiment history for a loop."""
    args = context.args
    name = args[0] if args else None
    
    if not name:
        await update.message.reply_text("Usage: /history <loop_name>")
        return

    loop = active_loops.get(name)
    if not loop or not loop.history:
        await update.message.reply_text(f"No history for '{name}'")
        return

    lines = [f"📜 **{name}** — {len(loop.history)} experiments\n", ""]
    for e in loop.history[-10:]:  # Last 10
        emoji = {"ship": "🚀", "continue": "🔄", "retrain": "🔁", "pivot": "↗️"}.get(
            e.decision.value if e.decision else "", "❓"
        )
        lines.append(f"{emoji} {e.id}: {e.decision.value if e.decision else '?'} — {e.reasoning[:80]}")
    
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Natural language chat — the bot understands loop engineering concepts."""
    text = update.message.text
    
    # Simple keyword-based responses for now
    text_lower = text.lower()
    
    if any(w in text_lower for w in ["hello", "hi", "hey"]):
        await update.message.reply_text(
            "Hey! I'm your loop engineering bot. Try /new to create a loop, "
            "or tell me what you're working on!"
        )
    elif any(w in text_lower for w in ["regressed", "worse", "bad result", "overfit"]):
        await update.message.reply_text(
            "Regression happens! Here's what I'd check:\n\n"
            "1. **Label quality** — is your teacher labeling too aggressively? (v9 was C3-only, overfit to 0.921)\n"
            "2. **Data diversity** — are you mixing in generic data? (v8 got 0.955 with 33% C3 + 67% generic)\n"
            "3. **Capacity** — bigger model ≠ better. ModernBERT-large (352M) got 0.906 vs base (149M) at 0.955\n"
            "4. **Epochs** — 3 epochs was the sweet spot. More epochs = overfitting.\n\n"
            "Try /decide <loop> to get the council's take!",
            parse_mode="Markdown",
        )
    elif any(w in text_lower for w in ["what next", "try", "idea", "suggest"]):
        await update.message.reply_text(
            "Ideas from the kompress loop:\n\n"
            "• **Better teacher** — Qwen3-Coder, GLM-5.2, Claude (v12 got 0.949)\n"
            "• **More data** — GLM-generated scenarios gave 0.951 (v13)\n"
            "• **Council** — let an LLM control the loop (v14 — concept proven!)\n"
            "• **New architecture** — try DeBERTa, RoBERTa, or a decoder-only model\n"
            "• **Different task** — apply the loop to something else entirely!\n\n"
            "Read the GUIDE: https://github.com/peterlodri-sec/loopkit/blob/main/GUIDE.md",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            "I'm a loop engineering bot. Try these:\n"
            "• /new <name> — start experimenting\n"
            "• \"my model regressed\" — get debugging advice\n"
            "• \"what should I try next?\" — get ideas\n"
            "• /decide <name> — council review",
        )


# ── Main ─────────────────────────────────────────────────────────────

def main():
    token = os.environ.get("LOOPKIT_BOT_TOKEN")
    if not token:
        print("Set LOOPKIT_BOT_TOKEN environment variable.")
        print("Get one from @BotFather on Telegram.")
        sys.exit(1)

    if not TELEGRAM_AVAILABLE:
        print("Install python-telegram-bot: pip install python-telegram-bot")
        sys.exit(1)

    app = Application.builder().token(token).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("new", new_loop))
    app.add_handler(CommandHandler("run", run_loop))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("decide", decide))
    app.add_handler(CommandHandler("history", history))
    app.add_handler(CommandHandler("loops", list_loops))

    # Natural chat
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    print("🤖 LoopKit Bot starting...")
    print(f"   Memory: {memory.db_path}")
    print(f"   Active loops: {len(active_loops)}")
    app.run_polling()


if __name__ == "__main__":
    main()
