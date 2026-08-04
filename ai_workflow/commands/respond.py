"""AI response to issue comments."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ai_workflow.gh_utils import GHClient, GHError

if TYPE_CHECKING:
    import argparse

    from ai_workflow.config import Config
    from ai_workflow.core import AIProvider
logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a helpful AI assistant responding to a user's comment on an issue.
- Provide helpful technical advice
- If suggesting code, use markdown code blocks with language identifiers
- If you need more information, ask specific questions
- Be concise but thorough
- If the issue is a duplicate, politely redirect
- If it's a usage question, point to relevant documentation"""


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the respond subcommand."""
    parser = subparsers.add_parser("respond", help="Respond to an issue comment")
    parser.add_argument("--issue-number", type=int, required=True)
    parser.add_argument("--comment", required=True, help="The comment to respond to")


def run(args: argparse.Namespace, config: Config, ai: AIProvider) -> int:
    """Generate and post an AI response to an issue comment."""
    gh = GHClient()
    try:
        issue = gh.issue_view(args.issue_number)
    except GHError as exc:
        logger.error("Failed to fetch issue: %s", exc)
        return 1
    context = issue.get("title", "")
    try:
        result = ai.chat(
            _SYSTEM_PROMPT,
            f"Issue context: {context}\n\nUser comment: {args.comment}",
            model=config.model_generic,
            temperature=0.4,
        )
    except Exception as exc:
        logger.error("AI respond failed: %s", exc)
        return 1
    if not result or not result.strip():
        logger.error("Empty AI response")
        return 1
    try:
        gh.issue_comment(args.issue_number, result)
    except GHError as exc:
        logger.error("Failed to post comment: %s", exc)
        return 1
    logger.info("Posted response on issue #%d", args.issue_number)
    return 0
