"""Welcome message for first-time contributors."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ai_workflow.gh_utils import GHClient, GHError

if TYPE_CHECKING:
    import argparse

    from ai_workflow.config import Config
    from ai_workflow.core import AIProvider
logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a welcoming community manager. "
    "A user has just made their first contribution. "
    "Generate a warm, personalized welcome message that:"
    "\n1. Thanks them for their contribution"
    "\n2. Gives a brief overview of the project"
    "\n3. Points to contributing guidelines (CONTRIBUTING.md)"
    "\n4. Encourages further involvement"
    "\nKeep it to 3-4 short paragraphs."
)


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the welcome subcommand."""
    p = subparsers.add_parser("welcome", help="Welcome first-time contributors")
    p.add_argument("--username", required=True, help="GitHub username")


def run(args: argparse.Namespace, config: Config, ai: AIProvider) -> int:
    """Post a welcome comment on the user's first issue or PR."""
    gh = GHClient()
    try:
        is_first = gh.user_is_first_time(args.username)
    except GHError as exc:
        logger.warning("Could not verify contribution history: %s", exc)
        is_first = True
    if not is_first:
        logger.info("%s is not a first-time contributor; skipping welcome", args.username)
        return 0
    try:
        result = ai.chat(
            _SYSTEM_PROMPT,
            f"New contributor: @{args.username}",
            model=config.model_generic,
            temperature=0.6,
        )
    except Exception as exc:
        logger.error("AI welcome failed: %s", exc)
        return 1
    if not result or not result.strip():
        logger.error("Empty AI response")
        return 1
    print(f"Welcome message for @{args.username}:\n\n{result}")
    return 0
