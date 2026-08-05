"""AI 每周代码摘要报告。"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ai_workflow.gh_utils import GHClient, GHError
from ai_workflow.git_utils import GitRepo

if TYPE_CHECKING:
    import argparse

    from ai_workflow.config import Config
    from ai_workflow.core import AIProvider
logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a project manager. Generate a weekly summary from the data below.
Format as markdown with sections:
## Overview
## Key Metrics
## Notable Changes
## Recommendations"""


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the summary subcommand."""
    parser = subparsers.add_parser("summary", help="生成每周摘要")
    parser.add_argument("--since", default="1 week ago", help="时间段起始")


def run(args: argparse.Namespace, config: Config, ai: AIProvider) -> int:
    """Generate a weekly summary and post it as a GitHub issue."""
    repo = GitRepo()
    if not repo.is_repo():
        logger.error("Not a git repository")
        return 1
    commits = repo.log(since=args.since)
    log_text = "\n".join(f"{c.hash[:8]} {c.message}" for c in commits) or "none"
    gh = GHClient()
    prs = issues = 0
    try:
        prs = len(gh.pr_list(state="merged", limit=100))
        issues = len(gh.issue_list(state="all", limit=100))
    except GHError as exc:
        logger.warning("Could not fetch GitHub metrics: %s", exc)
    context = (
        f"Period: {args.since} to now\n\n"
        f"## Commits\n{log_text}\n\n"
        f"## Merged PRs (recent): {prs}\n"
        f"## Issues (open/all): {issues}\n"
    )
    try:
        result = ai.chat(
            _SYSTEM_PROMPT,
            context,
            model=config.model_summary,
            temperature=0.3,
        )
    except Exception as exc:
        logger.error("AI summary failed: %s", exc)
        return 1
    if not result or not result.strip():
        logger.error("Empty AI response")
        return 1
    body = f"# Weekly Code Summary\n\n**Period**: {args.since} to now\n\n{result}"
    try:
        url = gh.issue_create(
            title=f"Weekly Summary ({args.since})",
            body=body,
            labels=["weekly-summary"],
        )
        logger.info("Posted weekly summary: %s", url)
    except GHError as exc:
        logger.error("Failed to create summary issue: %s", exc)
        print(body)
        return 1
    return 0
