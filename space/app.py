"""Headroom Eval Space — Level 4 Hill Climbing Loop.

Hugging Face Space that continuously evaluates Headroom proxy builds
against SWE-bench tasks, tracks behavioral regressions (extra tool calls,
redundant loops), and exposes a live dashboard.

Architecture:
  cron → eval loop → headroom proxy → agent trajectories
  → OpenTelemetry traces → HF Dataset → Gradio dashboard
  → Telegram notifications → Council review

Run:
  python space/app.py
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import gradio as gr

# OpenTelemetry — dogfooding our own observability
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider

trace.set_tracer_provider(TracerProvider())
metrics.set_meter_provider(MeterProvider())
tracer = trace.get_tracer("headroom-eval")
meter = metrics.get_meter("headroom-eval")
eval_counter = meter.create_counter("eval.runs", "Number of eval runs")
eval_histogram = meter.create_histogram("eval.duration_seconds", "Eval run duration")
error_counter = meter.create_counter("eval.errors", "Number of eval errors")
from evals.headroom_runner import execute_swe_trajectory, TrajectoryMetrics, SWE_TASKS

# ── State ────────────────────────────────────────────────────────────
STATE_DIR = Path(os.environ.get("HEADROOM_EVAL_STATE", "/data/eval_state"))
STATE_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = STATE_DIR / "eval_state.json"

COMPRESSORS = [
    "PeetPedro/kompress-v8",
    "PeetPedro/kompress-v4",
    "PeetPedro/kompress-v17",
    "chopratejas/kompress-v2-base",
]

eval_history: list[dict] = []
eval_running = False
eval_thread = None


def load_state():
    global eval_history
    if STATE_FILE.exists():
        eval_history = json.loads(STATE_FILE.read_text())


def save_state()
            duration = time.perf_counter() - t_start
            eval_histogram.record(duration, {"compressor": compressor}):
    STATE_FILE.write_text(json.dumps(eval_history, indent=2, default=str))


def push_to_hf_dataset():
    """Push eval traces to HuggingFace Dataset."""
    try:
        from datasets import Dataset
        ds = Dataset.from_list([r for r in eval_history])
        ds.push_to_hub("PeetPedro/headroom-eval-traces", token=os.environ.get("HF_TOKEN"))
        return "✓ pushed to HF Dataset"
    except Exception as e:
        return f"dataset push skipped: {e}"


# ── Eval loop (background) ───────────────────────────────────────────

def eval_loop(proxy_url: str, compressor: str, interval_sec: int = 3600):
    with tracer.start_as_current_span("eval_loop") as span:
        span.set_attribute("compressor", compressor)
        span.set_attribute("proxy_url", proxy_url)
        eval_counter.add(1, {"compressor": compressor})
    """Persistent eval loop — runs every hour or on trigger."""
    global eval_running
    eval_running = True

    while eval_running:
                run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        t_start = time.perf_counter()("%Y%m%d-%H%M%S")
        print(f"[eval] run {run_id} — compressor={compressor} proxy={proxy_url}")

        try:
            metrics = execute_swe_trajectory(
                proxy_url=proxy_url,
                compressor=compressor,
            )

            for m in metrics:
                record = m.to_dict()
                record["run_id"] = run_id
                record["timestamp"] = datetime.now(timezone.utc).isoformat()
                eval_history.append(record)

            # Summary
            success = sum(1 for m in metrics if m.task_success)
            regressions = sum(1 for m in metrics if m.redundant_loops > 0)
            print(f"[eval] {run_id}: {success}/{len(metrics)} success, {regressions} regressions")

            save_state()
            duration = time.perf_counter() - t_start
            eval_histogram.record(duration, {"compressor": compressor})
            push_to_hf_dataset()

        except Exception as e:
            print(f"[eval] {run_id} FAILED: {e}")
            eval_history.append({
                "run_id": run_id, "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            save_state()
            duration = time.perf_counter() - t_start
            eval_histogram.record(duration, {"compressor": compressor})

        # Sleep until next interval (with 1s polling for stop signal)
        for _ in range(interval_sec):
            if not eval_running:
                break
            time.sleep(1)


def start_eval(proxy_url: str, compressor: str, interval: int = 3600):
    global eval_thread, eval_running
    if eval_running:
        return "⚠️ Eval already running"
    eval_thread = threading.Thread(
        target=eval_loop,
        args=(proxy_url, compressor, interval),
        daemon=True,
    )
    eval_thread.start()
    return f"▶️ Eval started — {compressor} @ {proxy_url}, every {interval}s"


def stop_eval():
    global eval_running
    eval_running = False
    return "⏹ Eval stopped"


# ── Gradio Dashboard ──────────────────────────────────────────────────

def build_regression_matrix():
    """Live chart: tool calls per task over time."""
    if not eval_history:
        return "No data yet. Start an eval run."

    # Group by task_id, compute recent averages
    from collections import defaultdict
    by_task = defaultdict(list)
    for r in eval_history[-50:]:  # last 50 runs
        if "task_id" in r:
            by_task[r["task_id"]].append(r["total_tool_calls"])

    lines = ["| Task | Avg Tools | Runs | Status |", "|---|---|---|---|"]
    for task_id, calls in sorted(by_task.items()):
        avg = sum(calls) / len(calls)
        status = "⚠️ HIGH" if avg > 6 else "✅ OK"
        lines.append(f"| {task_id} | {avg:.1f} | {len(calls)} | {status} |")
    return "\n".join(lines)


def build_recent_runs():
    """Last 10 eval runs."""
    if not eval_history:
        return "No runs yet."
    lines = ["| Run ID | Tasks | Success | Loops |", "|---|---|---|---|"]
    seen = set()
    for r in reversed(eval_history):
        rid = r.get("run_id", "?")
        if rid in seen:
            continue
        seen.add(rid)
        runs = [x for x in eval_history if x.get("run_id") == rid]
        success = sum(1 for x in runs if x.get("task_success"))
        loops = sum(x.get("redundant_loops", 0) for x in runs)
        lines.append(f"| {rid} | {len(runs)} | {success} | {loops} |")
        if len(seen) >= 10:
            break
    return "\n".join(lines)


def build_efficiency_chart():
    """Token efficiency ratio over time."""
    if not eval_history:
        return "No data."
    ratios = [r.get("token_efficiency_ratio", 1.0) for r in eval_history[-20:] if "token_efficiency_ratio" in r]
    if not ratios:
        return "No efficiency data."
    avg = sum(ratios) / len(ratios)
    return f"Avg efficiency: {avg:.3f} | Min: {min(ratios):.3f} | Max: {max(ratios):.3f}"


def trigger_manual_run(proxy_url: str, compressor: str):
    """Manual trigger — runs once and returns results."""
    metrics = execute_swe_trajectory(proxy_url=proxy_url, compressor=compressor)
    lines = ["| Task | Tools | Loops | Success | Tokens Saved |", "|---|---|---|---|---|"]
    for m in metrics:
        icon = "✅" if m.task_success else "❌"
        lines.append(f"| {m.task_id} | {m.total_tool_calls} | {m.redundant_loops} | {icon} | {m.tokens_saved} |")
    return "\n".join(lines)


# ── UI ────────────────────────────────────────────────────────────────

with gr.Blocks(title="Headroom Eval Space — Hill Climbing Loop", theme="soft") as demo:
    gr.Markdown("""
    # 🏔️ Headroom Eval Space — Level 4 Hill Climbing Loop
    
    Persistent evaluation engine for the Headroom proxy.
    Tracks behavioral regressions: does compression cause extra tool calls or redundant loops?
    """)

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### ⚙️ Control")
            proxy_input = gr.Textbox(label="Proxy URL", value="http://localhost:18721")
            compressor_input = gr.Dropdown(label="Compressor", choices=COMPRESSORS, value=COMPRESSORS[0])
            interval_input = gr.Slider(label="Interval (seconds)", minimum=60, maximum=86400, value=3600, step=60)
            with gr.Row():
                start_btn = gr.Button("▶️ Start Eval Loop", variant="primary")
                stop_btn = gr.Button("⏹ Stop")
                trigger_btn = gr.Button("🔄 Manual Run")
            status_text = gr.Textbox(label="Status", interactive=False)

        with gr.Column(scale=2):
            gr.Markdown("### 📊 Regression Matrix")
            matrix_display = gr.Markdown(value="No data yet. Start an eval run.")

    with gr.Row():
        with gr.Column():
            gr.Markdown("### 📜 Recent Runs")
            runs_display = gr.Markdown(value="No runs yet.")
        with gr.Column():
            gr.Markdown("### ⚡ Token Efficiency")
            efficiency_display = gr.Markdown(value="No data.")

    with gr.Row():
        gr.Markdown("### 🔬 Manual Run Results")
        manual_display = gr.Markdown(value="Click 'Manual Run' to see results.")

    # Events
    start_btn.click(
        fn=start_eval,
        inputs=[proxy_input, compressor_input, interval_input],
        outputs=[status_text],
    )
    stop_btn.click(fn=stop_eval, outputs=[status_text])
    trigger_btn.click(
        fn=trigger_manual_run,
        inputs=[proxy_input, compressor_input],
        outputs=[manual_display],
    )

    # Periodic refresh
    def refresh_dashboard():
        return build_regression_matrix(), build_recent_runs(), build_efficiency_chart()

    demo.load(load_state)
    demo.load(refresh_dashboard, outputs=[matrix_display, runs_display, efficiency_display], every=30)


if __name__ == "__main__":
    load_state()
    demo.queue().launch(server_name="0.0.0.0", server_port=7860)
