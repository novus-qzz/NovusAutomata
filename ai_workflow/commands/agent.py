"""AI Agent orchestration engine.

Usage:
    ai-workflow agent --goal "Review PR #123 and auto-fix any issues"
    ai-workflow agent --goal "Triage all open issues and file bug reports"

The agent decomposes a natural-language goal into a command plan, executes each
step sequentially, feeds prior output into subsequent steps as context, and
produces a final summary report.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse

    from ai_workflow.config import Config
    from ai_workflow.core import AIProvider

from ai_workflow.core import extract_json

logger = logging.getLogger(__name__)

_PLAN_EMOJI = "\u2705"
_FAIL_EMOJI = "\u274c"
_ARROW_EMOJI = "\u2192"
_TBOX_EMOJI = "\u2514"
_BOLT_EMOJI = "\u26a1"

_AVAILABLE = {
    "audit", "diff", "review", "describe", "fix", "triage", "respond",
    "quality", "simplify", "issue2pr", "deps", "gentest", "securix",
    "commitlint", "health", "assign", "welcome", "changelog", "summary",
    "stale", "readme", "plan", "status",
}

_STEP_TIMEOUT = 300

_PLAN_PROMPT = (
    "You are an AI workflow orchestrator. A user has stated a goal. "
    "Break it down into concrete steps, each step being ONE of these commands:\n"
    "  audit diff review describe fix triage respond quality simplify issue2pr "
    "  deps gentest securix commitlint health assign welcome changelog "
    "  summary stale readme plan status\n"
    "For each step give the command name, shell-style args, and a one-line reason.\n"
    "Output ONLY a JSON object:\n"
    '{"plan":[{"command":"review","args":"--pr-number 123","reason":"inspect the PR"}],'
    '"rationale":"..."}'
)

_SUMMARY_PROMPT = (
    "You are a project manager. Given the step-by-step execution log below, "
    "produce a concise final report with:\n"
    "## Summary\n## Details\n## Issues\n## Recommendations"
)


@dataclass
class Step:
    """A single step in the agent's execution plan."""

    command: str
    args: str
    reason: str = ""
    status: str = "pending"
    output: str = ""
    error: str = ""
    elapsed: float = 0.0


def _parse_plan(text: str) -> list[tuple[str, str, str]]:
    """Extract [(command, args, reason), ...] from AI plan text."""
    try:
        data = extract_json(text)
    except json.JSONDecodeError:
        logger.warning("Plan not valid JSON; returning empty plan")
        return []
    plan = data.get("plan", [])
    if not isinstance(plan, list):
        return []
    steps: list[tuple[str, str, str]] = []
    for item in plan:
        cmd = item.get("command", "")
        if cmd not in _AVAILABLE:
            logger.warning("Unknown command in plan: %s; skipping", cmd)
            continue
        steps.append((cmd, item.get("args", ""), item.get("reason", "")))
    return steps


def _run_one(command: str, args_str: str, config: Config) -> Step:
    """Execute a single ai-workflow command and capture output."""
    step = Step(command=command, args=args_str)
    cmd = ["python", "-m", "ai_workflow", command, *args_str.split()]
    start = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=_STEP_TIMEOUT,
            env={**os.environ, "NVIDIA_API_KEY": config.nvidia_api_key},
        )
        step.output = proc.stdout + proc.stderr
        step.error = "" if proc.returncode == 0 else proc.stderr
        step.status = "success" if proc.returncode == 0 else "failed"
    except subprocess.TimeoutExpired:
        step.error = f"Timeout after {_STEP_TIMEOUT}s"
        step.status = "failed"
    except FileNotFoundError:
        step.error = "ai-workflow module not found"
        step.status = "failed"
    step.elapsed = round(time.monotonic() - start, 1)
    return step


def _progress_bar(steps: list[Step]) -> str:
    """Render a progress bar string for the agent's execution."""
    total = len(steps)
    done = sum(1 for s in steps if s.status != "pending")
    ok = sum(1 for s in steps if s.status == "success")
    bar_len = 20
    filled = max(0, min(bar_len, round(done / total * bar_len) if total else 0))
    bar = "#" * filled + "." * (bar_len - filled)
    lines = [f"[{bar}] {done}/{total} steps  ({ok} success)"]
    for s in steps:
        tag = _PLAN_EMOJI if s.status == "success" else (
            _FAIL_EMOJI if s.status == "failed" else "  "
        )
        lines.append(f"  {tag} {s.command} {s.args}")
    return "\n".join(lines)


def run(args: argparse.Namespace, config: Config, ai: AIProvider) -> int:
    """Run the AI agent: plan, execute, and report."""
    goal = getattr(args, "goal", "")
    if not goal:
        logger.error("--goal is required")
        return 1
    print(f"\n{_BOLT_EMOJI} AI Agent: {goal}\n")

    print("Planning...\n")
    try:
        plan_text = ai.chat(
            _PLAN_PROMPT,
            f"Goal: {goal}",
            model=config.model_generic,
            temperature=0.2,
        )
    except Exception as exc:
        logger.error("AI planning failed: %s", exc)
        return 1

    steps_data = _parse_plan(plan_text or "{}")
    steps: list[Step] = []
    for cmd, args_str, reason in steps_data:
        steps.append(Step(command=cmd, args=args_str, reason=reason))
    if not steps:
        print("No valid steps could be parsed. Raw AI output:")
        print(plan_text or "(empty)")
        return 0
    print(f"Plan: {len(steps)} step(s)\n")

    for i, step in enumerate(steps, 1):
        print(f"[{i}/{len(steps)}] {step.command} {step.args}")
        if step.reason:
            print(f"  {_ARROW_EMOJI} {step.reason}")
        _run_one(step.command, step.args, config)
        print(f"  {step.status} ({step.elapsed}s)")
        if step.error:
            err_preview = step.error[:200]
            print(f"  {_FAIL_EMOJI} {err_preview}")
        if step.output:
            preview = step.output[:200].strip()
            if preview:
                suffix = "..." if len(step.output) > 200 else ""
                print(f"  {_TBOX_EMOJI} {preview}{suffix}")
        print()

    print(_progress_bar(steps))
    print()

    ok = sum(1 for s in steps if s.status == "success")
    failed = sum(1 for s in steps if s.status == "failed")
    print(f"Result: {ok} success, {failed} failed\n")

    step_log_lines = []
    for s in steps:
        tag = _PLAN_EMOJI if s.status == "success" else _FAIL_EMOJI
        line = f"- {tag} {s.command} {s.args}: {s.reason} ({s.elapsed}s)"
        step_log_lines.append(line)
    step_log = "\n".join(step_log_lines)
    print("Generating summary...\n")
    try:
        report = ai.chat(
            _SUMMARY_PROMPT,
            step_log,
            model=config.model_generic,
            temperature=0.4,
        )
    except Exception as exc:
        logger.error("AI summary failed: %s", exc)
        report = "(summary generation failed)"
    print(report or step_log)
    return 0


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the agent subcommand."""
    p = subparsers.add_parser(
        "agent",
        help="AI agent: orchestrate multi-step workflows",
    )
    p.add_argument(
        "--goal",
        required=True,
        help="Describe what you want to accomplish",
    )
