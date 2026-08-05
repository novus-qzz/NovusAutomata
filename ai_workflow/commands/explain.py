"""AI code explanation with multiple detail levels."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ai_workflow.git_utils import GitRepo

if TYPE_CHECKING:
    import argparse

    from ai_workflow.config import Config
    from ai_workflow.core import AIProvider

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an expert code explainer.
Analyze the provided code and generate a comprehensive explanation.

Explanation levels:
- beginner: Simple language, focus on what the code does, avoid jargon
- intermediate: Technical details, patterns used, how it fits in larger context
- expert: Deep dive into algorithms, design decisions, edge cases, optimization

Output format (markdown):
## Overview
Brief description of what the code does.

## Key Components
- List of main functions/classes/components

## How It Works
Step-by-step explanation of the code flow.

## Usage Examples
Example scenarios where this code is used.

## Common Pitfalls
Potential issues or things to watch out for.

## Technical Details
- Time complexity
- Space complexity
- Design patterns used"""


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the explain subcommand."""
    p = subparsers.add_parser("explain", help="Explain code with AI")
    p.add_argument("--file", help="Path to file to explain")
    p.add_argument("--code", help="Code snippet to explain")
    p.add_argument(
        "--level",
        choices=["beginner", "intermediate", "expert"],
        default="intermediate",
        help="Explanation detail level",
    )
    p.add_argument("--pr-number", type=int, help="PR number to explain file from")


def run(args: argparse.Namespace, config: Config, ai: AIProvider) -> int:
    """Generate AI explanation of code."""
    code = ""
    source = ""

    if args.code:
        code = args.code
        source = "command line"
    elif args.file:
        try:
            with open(args.file, encoding="utf-8") as f:
                code = f.read()
            source = args.file
        except OSError as exc:
            logger.error("Failed to read file %s: %s", args.file, exc)
            return 1
    elif args.pr_number:
        from ai_workflow.gh_utils import GHClient, GHError

        gh = GHClient()
        try:
            diff = gh.pr_diff(args.pr_number)
        except GHError as exc:
            logger.error("Failed to fetch PR diff: %s", exc)
            return 1
        if not diff.strip():
            logger.info("No diff to explain for PR #%d", args.pr_number)
            return 0
        code = diff
        source = f"PR #{args.pr_number}"
    else:
        repo = GitRepo()
        if not repo.is_repo():
            logger.error("Not a git repository")
            return 1
        diff_result = repo.diff()
        code = "\n".join(f.content for f in diff_result.files if f.content)
        source = "working tree"
        if not code.strip():
            logger.info("No changes in the working tree")
            return 0

    if not code.strip():
        logger.error("No code to explain")
        return 1

    user_prompt = f"Explanation level: {args.level}\n\nSource: {source}\n\nCode:\n```\n{code}\n```"

    try:
        result = ai.chat(
            _SYSTEM_PROMPT,
            user_prompt,
            model=config.model_generic,
            temperature=0.3,
        )
    except Exception as exc:
        logger.error("AI explanation failed: %s", exc)
        return 1

    if not result or not result.strip():
        logger.error("Empty AI response")
        return 1

    print(f"## Code Explanation ({args.level} level)\n")
    print(result)
    return 0
