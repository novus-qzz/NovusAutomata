"""AI 生成的 PR 描述。"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ai_workflow.gh_utils import GHClient, GHError

if TYPE_CHECKING:
    import argparse

    from ai_workflow.config import Config
    from ai_workflow.core import AIProvider
logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a technical writer. Generate a PR description based on the diff.
Output in this exact format:

Title: <conventional-commit-type>: <brief description>

## Summary
<1-2 sentences>

## Changes
- file: <path> — <what changed and why>

## Type
<feat|fix|refactor|chore|docs|test|perf>

## Testing
<suggested testing approach>

## Breaking Changes
<Yes|No> — <details if Yes>"""


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the describe subcommand."""
    parser = subparsers.add_parser("describe", help="生成 PR 描述")
    parser.add_argument("--pr-number", type=int, required=True, help="要描述的 PR 编号")


def run(args: argparse.Namespace, config: Config, ai: AIProvider) -> int:
    """Generate and apply a PR description."""
    gh = GHClient()
    try:
        diff = gh.pr_diff(args.pr_number)
    except GHError as exc:
        logger.error("Failed to fetch PR data: %s", exc)
        return 1
    if not diff.strip():
        logger.info("No diff to describe for PR #%d", args.pr_number)
        return 0
    try:
        result = ai.chat(
            _SYSTEM_PROMPT,
            f"Diff:\n\n{diff}",
            model=config.model_fix,
            temperature=0.3,
        )
    except Exception as exc:
        logger.error("AI describe failed: %s", exc)
        return 1
    if not result or not result.strip():
        logger.error("Empty AI response")
        return 1

    title: str | None = None
    body = result
    lines = result.splitlines()
    for i, line in enumerate(lines):
        if line.lower().startswith("title:"):
            title = line.split(":", 1)[1].strip()
            body = "\n".join(lines[i + 1 :]).strip()
            break
    try:
        gh.pr_edit(args.pr_number, title=title, body=body)
    except GHError as exc:
        logger.error("Failed to update PR: %s", exc)
        return 1
    logger.info("Updated PR #%d description", args.pr_number)
    return 0
