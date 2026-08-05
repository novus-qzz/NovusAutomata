"""AI 修复安全扫描发现。"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING

from ai_workflow.git_utils import GitRepo
from ai_workflow.safe_io import SafeFileWriter

if TYPE_CHECKING:
    import argparse

    from ai_workflow.config import Config
    from ai_workflow.core import AIProvider
logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a security engineer. Fix the vulnerabilities reported below.
For each finding:
1. Analyze the vulnerability type
2. Generate a minimal, safe fix
3. Do not introduce new dependencies
4. Follow security best practices (input validation, parameterized queries)

Output format:
===FILE:path/to/file.py===
<fixed file content>
===END===
Only output files that need changes."""

_FILE_BLOCK = re.compile(r"===FILE:(.+?)===\n(.*?)\n===END===", re.DOTALL)


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the securix subcommand."""
    p = subparsers.add_parser("securix", help="修复安全发现")
    p.add_argument("--report", type=str, default="", help="扫描报告路径")


def run(args: argparse.Namespace, config: Config, ai: AIProvider) -> int:
    """Fix security findings from a scanner report or the working-tree diff."""
    repo = GitRepo()
    if not repo.is_repo():
        logger.error("Not a git repository")
        return 1
    findings = args.report
    if not findings:
        diff_result = repo.diff()
        findings = "\n".join(f.content for f in diff_result.files if f.content)
        if not findings.strip():
            logger.info("No diff to analyze for security")
            return 0
    else:
        try:
            with open(args.report, encoding="utf-8") as f:
                raw = f.read()
            try:
                data = json.loads(raw)
                findings = json.dumps(data, indent=2, default=str)
            except json.JSONDecodeError:
                findings = raw
        except OSError as exc:
            logger.error("Failed to read report: %s", exc)
            return 1
    try:
        result = ai.chat(
            _SYSTEM_PROMPT,
            f"Security findings:\n\n{findings}",
            model=config.model_security,
            temperature=0.1,
        )
    except Exception as exc:
        logger.error("AI security fix failed: %s", exc)
        return 1
    files: dict[str, str] = {}
    for match in _FILE_BLOCK.finditer(result or ""):
        files[match.group(1).strip()] = match.group(2)
    if not files:
        logger.info("No security fixes generated")
        return 0
    writer = SafeFileWriter(config)
    written = writer.write_batch(files)
    logger.info("Applied %d/%d security fixes", written, len(files))
    return 0 if written > 0 else 1
