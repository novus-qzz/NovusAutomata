"""AI issue triage: classify, label, and prioritize."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from ai_workflow.core import extract_json
from ai_workflow.gh_utils import GHClient, GHError
from ai_workflow.models import TriageResult

if TYPE_CHECKING:
    import argparse

    from ai_workflow.config import Config
    from ai_workflow.core import AIProvider
logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an issue triage assistant. Analyze the issue and output a JSON object
with exactly these fields (no other text):
{
  "labels": ["bug"|"enhancement"|"question"|"documentation"],
  "priority": "high"|"medium"|"low",
  "priority_reason": "<brief explanation>",
  "complexity": "low"|"medium"|"high",
  "is_duplicate": false,
  "needs_more_info": false,
  "summary": "<one-sentence summary>"
}

Priority guidelines:
- high: crash, data loss, security, production blocker
- medium: feature request, bug with workaround
- low: cosmetic, documentation, nice-to-have"""


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the triage subcommand."""
    parser = subparsers.add_parser("triage", help="Triage an issue")
    parser.add_argument("--issue-number", type=int, required=True, help="Issue number")


def run(args: argparse.Namespace, config: Config, ai: AIProvider) -> int:
    """Triage a GitHub issue by adding labels and posting a summary."""
    gh = GHClient()
    try:
        issue = gh.issue_view(args.issue_number)
    except GHError as exc:
        logger.error("Failed to fetch issue: %s", exc)
        return 1
    title = issue.get("title", "")
    body = issue.get("body", "")
    if not title:
        logger.warning("Issue #%d has no title", args.issue_number)
        return 1
    try:
        result = ai.chat(
            _SYSTEM_PROMPT,
            f"Title: {title}\n\nBody: {body}",
            model=config.model_triage,
            temperature=0.0,
        )
    except Exception as exc:
        logger.error("AI triage failed: %s", exc)
        return 1
    try:
        data = extract_json(result or "{}")
        triage = TriageResult(
            labels=data.get("labels", []),  # type: ignore[arg-type]
            priority=data.get("priority", "medium"),  # type: ignore[arg-type]
            complexity=data.get("complexity", "medium"),  # type: ignore[arg-type]
            is_duplicate=bool(data.get("is_duplicate", False)),
            needs_more_info=bool(data.get("needs_more_info", False)),
            summary=data.get("summary", ""),  # type: ignore[arg-type]
        )
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse triage JSON: %s", exc)
        gh.issue_comment(args.issue_number, f"## AI Triage\n\n{result}")
        return 1
    try:
        if triage.labels:
            gh.issue_edit(args.issue_number, add_labels=triage.labels)
        comment = (
            f"## AI Triage Summary\n\n"
            f"- **Priority**: {triage.priority}\n"
            f"- **Complexity**: {triage.complexity}\n"
            f"- **Duplicate**: {triage.is_duplicate}\n"
            f"- **Needs more info**: {triage.needs_more_info}\n\n"
            f"{triage.summary}"
        )
        gh.issue_comment(args.issue_number, comment)
    except GHError as exc:
        logger.error("Failed to update issue: %s", exc)
        return 1
    logger.info("Triaged issue #%d", args.issue_number)
    return 0
