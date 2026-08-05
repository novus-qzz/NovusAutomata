"""实时 CI 仪表板 — 从终端监控 GitHub Actions 运行。

用法:
    ai-workflow dashboard            # 默认分支
    ai-workflow dashboard --branch main
    ai-workflow dashboard --limit 10

显示最新工作流运行的实时表格，包含状态、名称、分支、事件和持续时间。
"""

from __future__ import annotations

import json
import logging
import subprocess
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse

    from ai_workflow.config import Config
    from ai_workflow.core import AIProvider

logger = logging.getLogger(__name__)

_STATUS_COLORS: dict[str, str] = {
    "success": "\033[32m",
    "failure": "\033[31m",
    "cancelled": "\033[35m",
    "skipped": "\033[90m",
    "in_progress": "\033[33m",
    "queued": "\033[33m",
    "completed": "\033[97m",
}
_RESET = "\033[0m"


def _colorize(status: str, text: str) -> str:
    """Return *text* wrapped in an ANSI color for *status*."""
    color = _STATUS_COLORS.get(status, _RESET)
    return f"{color}{text}{_RESET}"


def _table(
    headers: list[str],
    rows: list[list[str]],
    widths: list[int] | None = None,
) -> str:
    """Render a simple ASCII table."""
    if widths is None:
        all_rows = [*rows, headers]
        widths = [
            max(len(str(r[i])) for r in all_rows if i < len(r))
            for i in range(len(headers))
        ]
    sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    header = "|" + "|".join(
        f" {str(h).ljust(w)} " for h, w in zip(headers, widths, strict=True)
    ) + "|"
    lines = [sep, header, sep]
    for row in rows:
        cells = []
        for cell, w in zip(row, widths, strict=True):
            val = str(cell)[:w] if cell else ""
            cells.append(f" {val.ljust(w)} ")
        lines.append("|" + "|".join(cells) + "|")
        lines.append(sep)
    return "\n".join(lines)


def _fetch_runs(branch: str, limit: int) -> list[dict]:
    """Query GitHub API for recent workflow runs."""
    url = (
        f"https://api.github.com/repos/novus-qzz/NovusAutomata/actions/runs"
        f"?branch={branch}&per_page={limit}&status=in_progress,completed"
    )
    try:
        proc = subprocess.run(
            ["gh", "api", url, "--jq", "."],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if proc.returncode != 0:
            return []
        return json.loads(proc.stdout).get("workflow_runs", [])  # type: ignore[no-any-return]
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        return []


def _format_duration(seconds: int) -> str:
    """Convert seconds to a human-readable duration."""
    if seconds < 60:
        return f"{seconds}s"
    return f"{seconds // 60}m{seconds % 60}s"


def _format_timestamp(ts: str) -> str:
    """Format a GitHub timestamp to local time string."""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return ts


def _run_dashboard(args: argparse.Namespace) -> None:
    """Render the CI dashboard."""
    branch = getattr(args, "branch", "main") or "main"
    limit = getattr(args, "limit", 10) or 10

    runs = _fetch_runs(branch, limit)
    if not runs:
        print(f"\nNo runs found for branch '{branch}'.")
        print("Make sure you are authenticated with 'gh auth login'.\n")
        return

    rows: list[list[str]] = []
    for run in runs:
        name = run.get("name", "?")[:30]
        conclusion = run.get("conclusion", "?")
        branch_name = run.get("head_branch", "?")[:12]
        event = run.get("event", "?")[:12]
        display_title = run.get("display_title", "?")[:25]
        duration_raw = run.get("run_started_at", 0) - run.get("created_at", 0)
        duration = _format_duration(duration_raw)
        updated = _format_timestamp(run.get("updated_at", "?"))
        rows.append([name, conclusion, branch_name, event, display_title, duration, updated])

    headers = ["Workflow", "Status", "Branch", "Event", "Title", "Duration", "Updated"]
    table = _table(headers, rows)
    emoji = "\U0001F4CA"
    print(f"\n  {emoji} CI Dashboard — {branch} branch (last {limit} runs)\n")
    print(table)


def run(args: argparse.Namespace, config: Config, ai: AIProvider) -> int:
    """Main entry for the dashboard command."""
    _run_dashboard(args)
    return 0


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the dashboard subcommand."""
    p = subparsers.add_parser("dashboard", help="实时 CI 仪表板")
    p.add_argument(
        "--branch",
        default="main",
        help="要监控的分支（默认：main）",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=10,
        help="显示的运行数量（默认：10）",
    )
