"""Headroom Eval Space — Level 4 Hill Climbing Loop."""
from __future__ import annotations
import json, os, sys, threading, time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import gradio as gr
from headroom_runner import execute_swe_trajectory, TrajectoryMetrics, SWE_TASKS

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

def save_state():
    STATE_FILE.write_text(json.dumps(eval_history, indent=2, default=str))

def push_to_hf_dataset():
    try:
        from datasets import Dataset
        ds = Dataset.from_list([r for r in eval_history])
        ds.push_to_hub("PeetPedro/headroom-eval-traces", token=os.environ.get("HF_TOKEN"))
        return "pushed to HF Dataset"
    except Exception:
        return "dataset push skipped"

def eval_loop(proxy_url: str, compressor: str, interval_sec: int = 3600):
    global eval_running
    eval_running = True
    while eval_running:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        t_start = time.perf_counter()
        try:
            metrics = execute_swe_trajectory(proxy_url=proxy_url, compressor=compressor)
            for m in metrics:
                record = m.to_dict()
                record["run_id"] = run_id
                record["timestamp"] = datetime.now(timezone.utc).isoformat()
                eval_history.append(record)
            success = sum(1 for m in metrics if m.task_success)
            regressions = sum(1 for m in metrics if m.redundant_loops > 0)
            print(f"[eval] {run_id}: {success}/{len(metrics)} ok, {regressions} regressions, {time.perf_counter()-t_start:.1f}s")
            save_state()
            push_to_hf_dataset()
        except Exception as e:
            print(f"[eval] {run_id} FAILED: {e}")
        for _ in range(interval_sec):
            if not eval_running:
                break
            time.sleep(1)

def start_eval(proxy_url: str, compressor: str, interval: int = 3600):
    global eval_thread, eval_running
    if eval_running:
        return "Already running"
    eval_thread = threading.Thread(target=eval_loop, args=(proxy_url, compressor, interval), daemon=True)
    eval_thread.start()
    return f"Started {compressor} @ {proxy_url}"

def stop_eval():
    global eval_running
    eval_running = False
    return "Stopped"

def build_regression_matrix():
    if not eval_history:
        return "No data yet."
    from collections import defaultdict
    by_task = defaultdict(list)
    for r in eval_history[-50:]:
        if "task_id" in r:
            by_task[r["task_id"]].append(r["total_tool_calls"])
    lines = ["| Task | Avg Tools | Runs |", "|---|---|---|"]
    for tid, calls in sorted(by_task.items()):
        lines.append(f"| {tid} | {sum(calls)/len(calls):.1f} | {len(calls)} |")
    return "\n".join(lines)

def build_recent_runs():
    if not eval_history:
        return "No runs yet."
    lines = ["| Run | Tasks | Success | Loops |", "|---|---|---|---|"]
    seen = set()
    for r in reversed(eval_history):
        rid = r.get("run_id", "?")
        if rid in seen:
            continue
        seen.add(rid)
        runs = [x for x in eval_history if x.get("run_id") == rid]
        lines.append(f"| {rid} | {len(runs)} | {sum(1 for x in runs if x.get('task_success'))} | {sum(x.get('redundant_loops',0) for x in runs)} |")
        if len(seen) >= 10:
            break
    return "\n".join(lines)

def trigger_manual_run(proxy_url, compressor):
    metrics = execute_swe_trajectory(proxy_url=proxy_url, compressor=compressor)
    lines = ["| Task | Tools | Loops | OK |", "|---|---|---|---|"]
    for m in metrics:
        lines.append(f"| {m.task_id} | {m.total_tool_calls} | {m.redundant_loops} | {'yes' if m.task_success else 'no'} |")
    return "\n".join(lines)

def refresh_dashboard():
    return build_regression_matrix(), build_recent_runs()

with gr.Blocks(title="Headroom Eval Space", theme="soft") as demo:
    gr.Markdown("# Headroom Eval Space — Level 4 Hill Climbing Loop")
    with gr.Row():
        with gr.Column(scale=1):
            proxy = gr.Textbox(label="Proxy URL", value="http://localhost:18721")
            compressor = gr.Dropdown(label="Compressor", choices=COMPRESSORS, value=COMPRESSORS[0])
            interval = gr.Slider(label="Interval (s)", minimum=60, maximum=86400, value=3600, step=60)
            with gr.Row():
                start_btn = gr.Button("Start Loop", variant="primary")
                stop_btn = gr.Button("Stop")
                trigger_btn = gr.Button("Manual Run")
            status = gr.Textbox(label="Status", interactive=False)
        with gr.Column(scale=2):
            matrix = gr.Markdown("Regression matrix will appear here")
    with gr.Row():
        runs_display = gr.Markdown("Recent runs will appear here")
    manual_display = gr.Markdown("Manual run results")
    start_btn.click(fn=start_eval, inputs=[proxy, compressor, interval], outputs=[status])
    stop_btn.click(fn=stop_eval, outputs=[status])
    trigger_btn.click(fn=trigger_manual_run, inputs=[proxy, compressor], outputs=[manual_display])
    demo.load(load_state)
    demo.load(refresh_dashboard, outputs=[matrix, runs_display], every=30)

if __name__ == "__main__":
    load_state()
    demo.queue().launch(server_name="0.0.0.0", server_port=7860)
