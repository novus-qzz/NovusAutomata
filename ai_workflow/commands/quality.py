"""AI PR quality gate: multi-dimensional scoring."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from ai_workflow.core import extract_json
from ai_workflow.gh_utils import GHClient, GHError
from ai_workflow.models import QualityCheck, QualityReport

if TYPE_CHECKING:
    import argparse

    from ai_workflow.config import Config
    from ai_workflow.core import AIProvider
logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a code quality auditor. Analyze the diff and output a JSON object
with exactly these fields (no other text):
{
  "score": <0-100 overall>,
  "checks": {
    "code_style": {"score": <0-100>, "issues": ["..."]},
    "type_safety": {"score": <0-100>, "issues": ["..."]},
    "test_coverage": {"score": <0-100>, "issues": ["..."]},
    "complexity": {"score": <0-100>, "issues": ["..."]},
    "security": {"score": <0-100>, "issues": ["..."]},
    "duplication": {"score": <0-100>, "issues": ["..."]}
  },
  "summary": "<brief overview>"
}"""


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the quality subcommand."""
    parser = subparsers.add_parser("quality", help="PR quality gate")
    parser.add_argument("--pr-number", type=int, required=True, help="PR number")


def run(args: argparse.Namespace, config: Config, ai: AIProvider) -> int:
    """Score a PR and post the quality report."""
    gh = GHClient()
    try:
        diff = gh.pr_diff(args.pr_number)
    except GHError as exc:
        logger.error("Failed to fetch PR diff: %s", exc)
        return 1
    if not diff.strip():
        logger.info("No diff to score for PR #%d", args.pr_number)
        return 0
    try:
        result = ai.chat(
            _SYSTEM_PROMPT,
            f"Diff:\n\n{diff}",
            model=config.model_quality,
            temperature=0.0,
        )
    except Exception as exc:
        logger.error("AI quality gate failed: %s", exc)
        return 1
    try:
        data = extract_json(result or "{}")
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse quality JSON: %s", exc)
        return 1
    checks = {
        name: QualityCheck(score=ch.get("score", 0), issues=ch.get("issues", []))
        for name, ch in data.get("checks", {}).items()
    }
    report = QualityReport(
        overall_score=int(data.get("score", 0)),
        checks=checks,
        summary=data.get("summary", ""),  # type: ignore[arg-type]
        threshold=60,
    )

    lines = [
        f"## AI Quality Gate: **{report.overall_score}/100**",
        "",
        "| Check | Score | Issues |",
        "|-------|-------|--------|",
    ]
    for name, check in report.checks.items():
        label = name.replace("_", " ").title()
        issues = "; ".join(check.issues) or "None"
        lines.append(f"| {label} | {check.score}/100 | {issues} |")
    lines.append(f"\n**Summary**: {report.summary}")
    body = "\n".join(lines)
    try:
        gh.pr_review(args.pr_number, body)
        if not report.passed:
            logger.info("Quality gate FAILED: %d/100", report.overall_score)
            return 1
        logger.info("Quality gate passed: %d/100", report.overall_score)
    except GHError as exc:
        logger.error("Failed to post quality report: %s", exc)
        return 1
    return 0
