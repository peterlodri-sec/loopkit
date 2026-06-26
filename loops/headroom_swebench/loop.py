"""Headroom SWE-bench Loop — measures if compression breaks agent behavior.

Pattern: Run the same task with compression ON vs OFF → compare results.
If compression doesn't hurt task completion, it's safe. If it does, we
found a regression that needs fixing.

This is the "outer loop" for headroom — the benchmark that watches the
proxy for regressions, not just kompress.

Run it:
  python -m loops.headroom_swebench.loop
"""

import sys, json, time, subprocess, os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loops.base import Loop, Decision


@dataclass
class SWETask:
    """A task that an agent should be able to solve."""
    id: str
    repo: str
    issue: str
    description: str
    expected_files: list[str] = field(default_factory=list)
    expected_output: str = ""


# ── Sample tasks (real SWE-bench style, simplified for local testing) ──
SAMPLE_TASKS = [
    SWETask(
        id="fix-import-error",
        repo=".",
        issue="Module imports fail after refactor",
        description="Fix the import path in the module so it correctly imports from the utils package",
        expected_files=["src/utils.py"],
        expected_output="from .utils import helper",
    ),
    SWETask(
        id="add-error-handling",
        repo=".",
        issue="Function crashes on None input",
        description="Add error handling to the process_data function so it returns an empty dict instead of crashing on None input",
        expected_files=["src/processor.py"],
        expected_output="if data is None: return {}",
    ),
    SWETask(
        id="fix-off-by-one",
        repo=".",
        issue="Loop misses last element",
        description="Fix the loop boundary in the paginate function so it includes the last element",
        expected_files=["src/pagination.py"],
        expected_output="range(0, len(items), page_size)",
    ),
]


class HeadroomSWEBenchLoop(Loop):
    """The loop that answers: does compression break the agent?"""

    def __init__(self, proxy_url: str = "http://127.0.0.1:18721"):
        super().__init__("headroom-swebench")
        self.proxy_url = proxy_url
        self.tasks = SAMPLE_TASKS

    def plan(self, context: dict) -> dict:
        task_idx = len(self.history) % len(self.tasks)
        task = self.tasks[task_idx]
        return {
            "task_id": task.id,
            "task_description": task.description,
            "repo": task.repo,
            "runs": [
                {"name": "baseline", "compression": False},
                {"name": "compressed", "compression": True},
            ],
        }

    def execute(self, plan: dict) -> dict:
        results = []
        for run_config in plan["runs"]:
            t0 = time.perf_counter()
            result = self._run_task(
                task_id=plan["task_id"],
                description=plan["task_description"],
                compression=run_config["compression"],
            )
            result["name"] = run_config["name"]
            result["duration_sec"] = round(time.perf_counter() - t0, 2)
            results.append(result)

        return {"task_id": plan["task_id"], "runs": results}

    def evaluate(self, results: dict) -> dict:
        runs = results["runs"]
        baseline = next((r for r in runs if r["name"] == "baseline"), None)
        compressed = next((r for r in runs if r["name"] == "compressed"), None)

        if not baseline or not compressed:
            return {"error": "missing runs"}

        # Key metrics
        token_diff = compressed.get("tokens_used", 0) - baseline.get("tokens_used", 0)
        tool_diff = compressed.get("tool_calls", 0) - baseline.get("tool_calls", 0)
        time_diff = compressed.get("duration_sec", 0) - baseline.get("duration_sec", 0)

        both_solved = baseline.get("solved", False) and compressed.get("solved", False)
        compression_broke_it = baseline.get("solved", False) and not compressed.get("solved", False)

        return {
            "task": results["task_id"],
            "baseline_solved": baseline.get("solved", False),
            "compressed_solved": compressed.get("solved", False),
            "both_solved": both_solved,
            "compression_broke_it": compression_broke_it,
            "token_savings_pct": round(
                (1 - compressed.get("tokens_used", 0) / max(baseline.get("tokens_used", 0), 1)) * 100, 1
            ),
            "tool_call_diff": tool_diff,
            "time_diff_sec": round(time_diff, 2),
        }

    def decide(self, metrics: dict, history: list) -> tuple[Decision, str]:
        if metrics.get("compression_broke_it"):
            return Decision.CONTINUE, (
                f"⚠️ Compression broke task {metrics['task']}! "
                f"Baseline solved it, compressed didn't. Investigate."
            )
        if metrics.get("both_solved"):
            savings = metrics.get("token_savings_pct", 0)
            return Decision.SHIP, (
                f"✅ Both solved {metrics['task']}. "
                f"Compression saved {savings}% tokens with no regression."
            )
        return Decision.CONTINUE, f"Neither solved {metrics['task']}. Task may need refinement."

    def _run_task(self, task_id: str, description: str, compression: bool) -> dict:
        """Simulate an agent solving a task through headroom proxy.

        In production, this would:
        1. Start headroom proxy with/without compression
        2. Run Claude Code or Codex on the task
        3. Measure tool calls, tokens, time, success

        For the template, we simulate with representative metrics.
        """
        # Simulated agent run
        # In production: actual LLM calls through the proxy
        base_tokens = 5000  # typical SWE-bench task
        base_tools = 8

        if compression:
            # With kompress v8: ~15% token savings on coding tasks
            tokens_used = int(base_tokens * 0.85)
            tool_calls = base_tools  # ideally no extra tool calls
            # Simulate: 95% chance compression doesn't cause extra tools
            if __import__('random').random() < 0.05:
                tool_calls += 1  # 5% chance of extra tool call from lost context
        else:
            tokens_used = base_tokens
            tool_calls = base_tools

        solved = __import__('random').random() > 0.15  # 85% solve rate

        return {
            "task_id": task_id,
            "compression_enabled": compression,
            "tokens_used": tokens_used,
            "tool_calls": tool_calls,
            "solved": solved,
            "note": "simulated — replace with real agent run through proxy",
        }


if __name__ == "__main__":
    loop = HeadroomSWEBenchLoop()
    print("🧪 Headroom SWE-bench — does compression break agents?\n")

    for i in range(3):
        exp = loop.run()
        m = loop.evaluate(exp.results)
        status = "⚠️ BROKEN" if m.get("compression_broke_it") else "✅ OK"
        print(f"  {exp.id}: {m.get('task', '?')} → {status} "
              f"(saved {m.get('token_savings_pct', 0)}% tokens)")

    safe = all(
        not loop.evaluate(e.results).get("compression_broke_it", False)
        for e in loop.history
    )
    print(f"\nVerdict: {'compression is safe' if safe else 'compression causes regressions — investigate!'}")
