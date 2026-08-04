"""Suggest PR reviewers based on diff history."""

from __future__ import annotations

import logging
import subprocess
from collections import Counter
from typing import TYPE_CHECKING

from ai_workflow.gh_utils import GHClient, GHError
from ai_workflow.git_utils import GitRepo

if TYPE_CHECKING:
    import argparse

    from ai_workflow.config import Config
    from ai_workflow.core import AIProvider
logger = logging.getLogger(__name__)


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the assign subcommand."""
    parser = subparsers.add_parser("assign", help="Suggest PR reviewers")
    parser.add_argument("--pr-number", type=int, required=True, help="PR number")


def _git_blame_authors(path: str, limit: int = 5) -> list[str]:
    """Return the top authors who last touched a file via git log."""
    try:
        result = subprocess.run(
            ["git", "log", "--pretty=%an", "-n", "8", "--", path],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    return [line for line in result.stdout.splitlines() if line]


def run(args: argparse.Namespace, config: Config, ai: AIProvider) -> int:
    """Recommend reviewers for a PR based on touched files' history."""
    gh = GHClient()
    repo = GitRepo()
    if not repo.is_repo():
        logger.error("Not a git repository")
        return 1
    try:
        diff_result = repo.diff(base_ref="refs/remotes/origin/main")
    except Exception:
        diff_result = repo.diff()
    if diff_result.is_empty():
        logger.info("No files to analyze")
        return 0
    counter: Counter[str] = Counter()
    for file in diff_result.files:
        for author in _git_blame_authors(file.path):
            counter[author] += 1
    if not counter:
        logger.info("No historical authors found for changed files")
        return 1
    suggestions = [a for a, _ in counter.most_common(3)]
    print("Suggested reviewers:")
    for s in suggestions:
        print(f"- @{s}")
    try:
        gh.pr_edit(args.pr_number, body=None, title=None)  # no-op to confirm access
    except GHError as exc:
        logger.error("Cannot access PR: %s", exc)
        return 1
    return 0
