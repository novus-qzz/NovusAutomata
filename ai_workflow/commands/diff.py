"""Show a summary of the working-tree diff."""

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
    """Register the diff subcommand."""
    subparsers.add_parser("diff", help="Show a summary of the working-tree diff")


def run(args: argparse.Namespace, config: Config, ai: AIProvider) -> int:
    """Print a human-readable diff summary."""
    repo = GitRepo()
    if not repo.is_repo():
        logger.error("Not a git repository")
        return 1
    result = repo.diff()
    if result.is_empty():
        logger.info("No changes in the working tree")
        return 0
    print("## Working-tree diff summary\n\n")
    print(f"- Files changed: {len(result.files)}")
    print(f"- Lines added: {result.total_additions}")
    print(f"- Lines deleted: {result.total_deletions}")
    print()
    for f in result.files:
        status = "+" if f.additions > f.deletions else "-"
        print(f"  {status} {f.path} (+{f.additions}/-{f.deletions})")
    return 0
