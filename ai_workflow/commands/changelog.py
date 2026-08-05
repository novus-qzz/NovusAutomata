"""AI 生成的变更日志条目。"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ai_workflow.git_utils import GitRepo

if TYPE_CHECKING:
    import argparse

    from ai_workflow.config import Config
    from ai_workflow.core import AIProvider
logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a release manager. Generate a CHANGELOG entry from the commit log.
Group commits by type:
- feat -> ## Features
- fix -> ## Bug Fixes
- docs -> ## Documentation
- refactor -> ## Refactoring
- test -> ## Tests
- perf -> ## Performance
- chore/ci/style/build -> ## Maintenance

For each entry, summarize the user-facing impact in one line.
Format as markdown."""


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the changelog subcommand."""
    parser = subparsers.add_parser("changelog", help="生成变更日志条目")
    parser.add_argument("--from-tag", default="", help="起始标签（空 = 最早）")
    parser.add_argument("--to-tag", default="", help="结束标签或 HEAD")


def run(args: argparse.Namespace, config: Config, ai: AIProvider) -> int:
    """Generate and write a CHANGELOG.md entry."""
    repo = GitRepo()
    if not repo.is_repo():
        logger.error("Not a git repository")
        return 1
    from_tag = args.from_tag or None
    to_tag = args.to_tag or None
    commits = repo.log(from_tag=from_tag, to_tag=to_tag)
    if not commits:
        logger.info("No commits found between the given refs")
        return 0
    log_text = "\n".join(f"{c.hash[:8]} {c.message}" for c in commits)
    try:
        result = ai.chat(
            _SYSTEM_PROMPT,
            f"Commits:\n\n{log_text}",
            model=config.model_changelog,
            temperature=0.2,
        )
    except Exception as exc:
        logger.error("AI changelog failed: %s", exc)
        return 1
    if not result or not result.strip():
        logger.error("Empty AI response")
        return 1
    header = f"## {to_tag or 'Unreleased'}\n\n"
    try:
        with open("CHANGELOG.md", encoding="utf-8") as f:
            existing = f.read()
        content = header + result.strip() + "\n\n" + existing
    except OSError:
        content = "# Changelog\n\n" + header + result.strip() + "\n"
    with open("CHANGELOG.md", "w", encoding="utf-8") as f:
        f.write(content)
    logger.info("Updated CHANGELOG.md")
    return 0
