"""Show repository health status."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse

    from ai_workflow.config import Config
    from ai_workflow.core import AIProvider


from ai_workflow.git_utils import GitRepo

logger = logging.getLogger(__name__)


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the status subcommand."""
    subparsers.add_parser("status", help="Show repository health status")


def run(args: argparse.Namespace, config: Config, ai: AIProvider) -> int:
    """Print a repository status dashboard."""
    repo = GitRepo()
    if not repo.is_repo():
        logger.error("Not a git repository")
        return 1
    branch = repo.current_branch()
    clean = repo.is_clean()
    status = repo.status()
    commits = repo.log(max_count=50)
    last = commits[-1] if commits else None
    contributors = len({c.author for c in commits})
    print("## Repository Status\n\n")
    print(f"- Branch: `{branch}`")
    print(f"- Working tree: {'clean' if clean else 'dirty'}")
    if status:
        print(f"- Uncommitted changes: {status}")
    if last:
        print(f"- Last commit: `{last.hash[:8]}` — {last.message}")
        print(f"- Authors (last 50): {contributors}")
    return 0
