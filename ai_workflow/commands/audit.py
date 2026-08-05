"""AI security audit from a scanner report."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse

    from ai_workflow.config import Config
    from ai_workflow.core import AIProvider


from ai_workflow.git_utils import GitRepo

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a security auditor. Analyze the dependency audit report and "
    "produce a concise security advisory report. "
    "For each vulnerable package, output: package, current version, "
    "vulnerable version(s), severity, CVE if available, recommended fix. "
    "Format as markdown table."
)


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the audit subcommand."""
    subparsers.add_parser("audit", help="Security audit from scanner report")


def run(args: argparse.Namespace, config: Config, ai: AIProvider) -> int:
    """Analyze a dependency audit report and generate a security advisory."""
    report_path = getattr(args, "report", "") or ""
    repo = GitRepo()
    if not repo.is_repo():
        logger.error("Not a git repository")
        return 1
    if not report_path:
        logger.error("--report is required")
        return 1
    try:
        with open(report_path, encoding="utf-8") as f:
            raw = f.read()
    except OSError as exc:
        logger.error("Failed to read report: %s", exc)
        return 1
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {}
    findings = data.get("dependencies", [])
    vulns = [d for d in findings if d.get("vulns")]
    if not vulns:
        logger.info("No vulnerable dependencies found")
        return 0
    lines = [f"# Vulnerable Dependency Report\n\n{len(vulns)} vulnerable package(s) found.\n"]
    for v in vulns:
        pkg = v.get("name", "?")
        version = v.get("version", "?")
        sev = v.get("severity", "?")
        cve = v.get("id", "?")
        lines.append(f"- **{pkg}** {version} | Severity: {sev} | CVE: {cve}")
    context = "\n".join(lines)
    try:
        result = ai.chat(
            _SYSTEM_PROMPT,
            context,
            model=config.model_security,
            temperature=0.2,
        )
    except Exception as exc:
        logger.error("AI audit failed: %s", exc)
        return 1
    print(result or context)
    return 0
