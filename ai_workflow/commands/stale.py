"""过期问题和 PR 管理。"""

from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING

from ai_workflow.gh_utils import GHClient, GHError

if TYPE_CHECKING:
    import argparse

    from ai_workflow.config import Config
    from ai_workflow.core import AIProvider
logger = logging.getLogger(__name__)

_SKIP_LABELS = {"bug", "enhancement", "security", "pinned", "weekly-summary"}


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the stale subcommand."""
    parser = subparsers.add_parser("stale", help="管理过期问题/PR")
    parser.add_argument("--days", type=int, default=30, help="不活跃阈值（天）")


def run(args: argparse.Namespace, config: Config, ai: AIProvider) -> int:
    """Mark stale issues/PRs and close ones that have been stale too long."""
    gh = GHClient()
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=args.days)
    try:
        issues = gh.issue_list(state="open", limit=50)
    except GHError as exc:
        logger.error("Failed to list issues: %s", exc)
        return 1
    marked = 0
    for item in issues:
        raw_number = item.get("number")
        if not isinstance(raw_number, int):
            continue
        number = raw_number
        title = item.get("title", "")
        raw_labels = item.get("labels")
        if not isinstance(raw_labels, list):
            continue
        labels = {
            str(label.get("name", ""))
            for label in raw_labels
        }
        if labels & _SKIP_LABELS or "stale" in labels:
            continue
        raw_updated = item.get("updatedAt", "")
        if not isinstance(raw_updated, str):
            continue
        updated = raw_updated
        try:
            updated_dt = datetime.datetime.fromisoformat(updated.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue
        if updated_dt > cutoff:
            continue
        try:
            gh.issue_edit(number, add_labels=["stale"])
            gh.issue_comment(
                number,
                f"This issue has been inactive for {args.days} days. "
                f"Marking as stale. It will be closed in 7 days if no activity.",
            )
        except GHError as exc:
            logger.warning("Failed to mark #%d stale: %s", number, exc)
            continue
        marked += 1
        logger.info("Marked #%d as stale: %s", number, title)
    if marked == 0:
        logger.info("No stale issues found")
    return 0
