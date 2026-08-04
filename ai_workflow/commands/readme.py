"""AI README synchronization with code changes."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ai_workflow.git_utils import GitRepo

if TYPE_CHECKING:
    import argparse

    from ai_workflow.config import Config
    from ai_workflow.core import AIProvider
logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a technical documentation writer. Analyze the code changes below and
the current README. If the README needs updating to stay accurate, output the FULL
new README.md content. If no update is needed, output exactly: NO_UPDATE"""


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the readme subcommand."""
    subparsers.add_parser("readme", help="Sync README with code changes")


def run(args: argparse.Namespace, config: Config, ai: AIProvider) -> int:
    """Update README.md to reflect recent code changes when needed."""
    repo = GitRepo()
    if not repo.is_repo():
        logger.error("Not a git repository")
        return 1
    try:
        with open("README.md", encoding="utf-8") as f:
            current_readme = f.read()
    except OSError:
        current_readme = ""
    diff_result = repo.diff()
    diff_text = "\n".join(f.content for f in diff_result.files if f.content)
    if not diff_text.strip():
        logger.info("No diff to sync")
        return 0
    context = f"Current README:\n{current_readme or '<none>'}\n\nRecent changes:\n{diff_text}"
    try:
        result = ai.chat(
            _SYSTEM_PROMPT,
            context,
            model=config.model_generic,
            temperature=0.2,
        )
    except Exception as exc:
        logger.error("AI readme sync failed: %s", exc)
        return 1
    if not result or "NO_UPDATE" in result:
        logger.info("README does not need updating")
        return 0
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(result)
    logger.info("README.md updated")
    return 0
