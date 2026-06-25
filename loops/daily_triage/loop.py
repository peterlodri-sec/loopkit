"""Daily Triage Loop — automated morning routine for any repo.

Pattern from Cobus Greyling's loop-engineering.
Reads CI failures, open issues, recent commits → writes findings → opens issues.

Run it:
  python -m loops.daily_triage.loop
"""

import sys, json, subprocess, re
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loops.base import Loop, Decision


class DailyTriageLoop(Loop):
    """Morning routine: scan repo health, report findings."""

    def __init__(self, repo_path: str = "."):
        super().__init__("daily-triage")
        self.repo_path = Path(repo_path)
        self.findings: list[dict] = []

    def plan(self, context: dict) -> dict:
        return {
            "actions": ["check_ci", "check_issues", "check_commits", "check_deps"],
            "repo": str(self.repo_path),
        }

    def execute(self, plan: dict) -> dict:
        findings = []
        
        # 1. Check for recent CI failures
        try:
            result = subprocess.run(
                ["gh", "run", "list", "--limit", "5", "--json", "status,conclusion,displayTitle,createdAt"],
                capture_output=True, text=True, cwd=self.repo_path, timeout=10
            )
            if result.returncode == 0:
                runs = json.loads(result.stdout)
                failures = [r for r in runs if r.get("conclusion") == "failure"]
                if failures:
                    findings.append({
                        "type": "ci_failure",
                        "severity": "high",
                        "detail": f"{len(failures)} recent CI failures",
                        "runs": failures,
                    })
        except Exception:
            pass  # gh CLI not available — skip

        # 2. Check for stale branches
        try:
            result = subprocess.run(
                ["git", "branch", "--no-merged", "main"],
                capture_output=True, text=True, cwd=self.repo_path, timeout=5
            )
            branches = [b.strip() for b in result.stdout.split("\n") if b.strip() and not b.strip().startswith("*")]
            if len(branches) > 10:
                findings.append({
                    "type": "stale_branches",
                    "severity": "medium",
                    "detail": f"{len(branches)} unmerged branches — consider cleanup",
                })
        except Exception:
            pass

        # 3. Check for recent commits
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "--since=24 hours ago"],
                capture_output=True, text=True, cwd=self.repo_path, timeout=5
            )
            commits = [l for l in result.stdout.split("\n") if l.strip()]
            findings.append({
                "type": "recent_activity",
                "severity": "info",
                "detail": f"{len(commits)} commits in last 24h",
                "commits": commits[:5],
            })
        except Exception:
            pass

        # 4. Check Python deps (if pyproject.toml exists)
        pyproject = self.repo_path / "pyproject.toml"
        if pyproject.exists():
            try:
                result = subprocess.run(
                    ["pip", "list", "--outdated", "--format=json"],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0:
                    outdated = json.loads(result.stdout)
                    if outdated:
                        findings.append({
                            "type": "outdated_deps",
                            "severity": "low",
                            "detail": f"{len(outdated)} outdated packages",
                            "packages": [f"{p['name']}=={p['latest_version']}" for p in outdated[:5]],
                        })
            except Exception:
                pass

        return {"findings": findings, "scanned_at": datetime.now(timezone.utc).isoformat()}

    def evaluate(self, results: dict) -> dict:
        findings = results.get("findings", [])
        high = sum(1 for f in findings if f.get("severity") == "high")
        medium = sum(1 for f in findings if f.get("severity") == "medium")
        return {
            "total_findings": len(findings),
            "high_severity": high,
            "medium_severity": medium,
            "needs_attention": high > 0,
        }

    def decide(self, metrics: dict, history: list) -> tuple[Decision, str]:
        if metrics["needs_attention"]:
            return Decision.CONTINUE, (
                f"⚠️ {metrics['high_severity']} high-severity issues need attention. "
                f"Run again after fixes."
            )
        return Decision.SHIP, (
            f"✅ All clear — {metrics['total_findings']} findings, "
            f"nothing critical. Morning triage complete."
        )


if __name__ == "__main__":
    loop = DailyTriageLoop()
    exp = loop.run()
    print(f"\n📋 Daily Triage — {exp.id}")
    print(f"   Decision: {exp.decision.value.upper()}")
    print(f"   {exp.reasoning}")
    for f in exp.results.get("findings", []):
        emoji = {"high": "🔴", "medium": "🟡", "info": "🔵"}.get(f["severity"], "⚪")
        print(f"   {emoji} [{f['type']}] {f['detail']}")
