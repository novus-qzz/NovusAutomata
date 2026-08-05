"""AI 驱动的 PR 代码审查。"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ai_workflow.gh_utils import GHClient, GHError

if TYPE_CHECKING:
    import argparse

    from ai_workflow.config import Config
    from ai_workflow.core import AIProvider
logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a senior software engineer conducting a thorough code review.
Analyze the diff for:
1. Logic errors and bugs
2. Edge cases and boundary conditions
3. Security vulnerabilities (injection, XSS, hardcoded secrets)
4. Performance issues
5. Code style violations
6. Missing tests or error handling gaps

For each issue, output in this exact format:
- File: <path> | Line: <number> | Severity: <CRITICAL|WARNING|SUGGESTION>
  Issue: <description>
  Suggestion: <concrete fix>

If no issues are found, output exactly: NO_ISSUES_FOUND"""


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the review subcommand."""
    parser = subparsers.add_parser("review", help="AI 代码审查")
    parser.add_argument("--pr-number", type=int, required=True, help="要审查的 PR 编号")


def run(args: argparse.Namespace, config: Config, ai: AIProvider) -> int:
    """Execute an AI review of a PR."""
    gh = GHClient()
    try:
        diff = gh.pr_diff(args.pr_number)
    except GHError as exc:
        logger.error("Failed to fetch PR diff: %s", exc)
        return 1
    if not diff.strip():
        logger.info("No diff to review for PR #%d", args.pr_number)
        return 0
    lines = diff.splitlines()
    if len(lines) > config.max_diff_size:
        logger.warning("Large diff (%d lines), truncating", len(lines))
        diff = "\n".join(lines[: config.max_diff_size])
    try:
        result = ai.chat(
            _SYSTEM_PROMPT,
            f"Review this diff:\n\n{diff}",
            model=config.model_review,
            temperature=0.1,
        )
    except Exception as exc:
        logger.error("AI review failed: %s", exc)
        return 1
    if result is None or not result.strip():
        logger.error("Empty AI response")
        return 1
    if "NO_ISSUES_FOUND" in result:
        gh.pr_review(args.pr_number, "## AI Review\n\nNo issues found. Looks good!")
        logger.info("No issues found in PR #%d", args.pr_number)
        return 0
    body = f"## AI Code Review\n\n{result}"
    gh.pr_review(args.pr_number, body)
    logger.info("Posted review on PR #%d", args.pr_number)
    return 0
