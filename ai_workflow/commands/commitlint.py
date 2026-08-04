"""AI commit message linting (Conventional Commits)."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from ai_workflow.git_utils import GitRepo

if TYPE_CHECKING:
    import argparse

    from ai_workflow.config import Config
    from ai_workflow.core import AIProvider
logger = logging.getLogger(__name__)

_TYPES = {
    "feat",
    "fix",
    "chore",
    "docs",
    "refactor",
    "test",
    "style",
    "perf",
    "ci",
    "build",
    "revert",
}
_HEADER_RE = re.compile(r"^([a-z]+)(?:\(([^)]+)\))?!?: (.+)$")


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the commitlint subcommand."""
    subparsers.add_parser("commitlint", help="Lint commit messages")


def run(args: argparse.Namespace, config: Config, ai: AIProvider) -> int:
    """Validate recent commit messages against Conventional Commits."""
    repo = GitRepo()
    if not repo.is_repo():
        logger.error("Not a git repository")
        return 1
    commits = repo.log(max_count=10)
    violations: list[str] = []
    for commit in commits:
        first_line = commit.message.splitlines()[0]
        match = _HEADER_RE.match(first_line)
        if not match:
            violations.append(f"{commit.hash[:8]}: non-conventional: {first_line}")
            continue
        commit_type = match.group(1)
        if commit_type not in _TYPES:
            violations.append(f"{commit.hash[:8]}: unknown type '{commit_type}': {first_line}")
        if len(first_line) > 72:
            violations.append(f"{commit.hash[:8]}: header too long ({len(first_line)} chars)")
    if not violations:
        logger.info("All commit messages are conventional")
        return 0
    logger.warning("Found %d commit message violation(s)", len(violations))
    for v in violations:
        print(v)
    return 1
