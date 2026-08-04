"""AI auto-fix for code issues in a PR or the working tree."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from ai_workflow.gh_utils import GHClient, GHError
from ai_workflow.git_utils import GitRepo
from ai_workflow.safe_io import SafeFileWriter

if TYPE_CHECKING:
    import argparse

    from ai_workflow.config import Config
    from ai_workflow.core import AIProvider
logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an expert programmer. Fix the issues in the following diff.
Rules:
1. Only modify files shown in the diff
2. Do not add new files
3. Do not modify configuration files or protected paths
4. Output each file change in this exact format:

===FILE:path/to/file.py===
<complete fixed file content>
===END===

5. Only output files that need changes
6. Preserve all existing imports and type annotations
7. Keep fixes minimal"""

_FILE_BLOCK = re.compile(r"===FILE:(.+?)===\n(.*?)\n===END===", re.DOTALL)


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the fix subcommand."""
    parser = subparsers.add_parser("fix", help="Auto-fix code issues")
    parser.add_argument("--pr-number", type=int, default=0, help="PR number (0 = working tree)")


def _parse_fixes(output: str) -> dict[str, str]:
    """Parse AI output into {path: content}."""
    files: dict[str, str] = {}
    for match in _FILE_BLOCK.finditer(output):
        path = match.group(1).strip()
        content = match.group(2)
        files[path] = content
    return files


def _run_tests() -> tuple[int, str]:
    """Run pytest and return (exit_code, output)."""
    import subprocess

    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "-q"],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        return result.returncode, result.stdout + result.stderr
    except FileNotFoundError:
        return -1, "pytest not available"


def run(args: argparse.Namespace, config: Config, ai: AIProvider) -> int:
    """Fix issues in the given PR or working tree."""
    repo = GitRepo()
    if not repo.is_repo():
        logger.error("Not a git repository")
        return 1

    diff_text: str
    if args.pr_number:
        try:
            diff_text = GHClient().pr_diff(args.pr_number)
        except GHError as exc:
            logger.error("Failed to fetch PR diff: %s", exc)
            return 1
    else:
        diff_result = repo.diff()
        diff_text = "\n".join(f.content for f in diff_result.files if f.content)
    if not diff_text.strip():
        logger.info("No diff to fix")
        return 0

    writer = SafeFileWriter(config)
    retries = config.max_fix_retries
    attempt = 0
    while attempt <= retries:
        try:
            result = ai.chat(
                _SYSTEM_PROMPT,
                f"Fix this diff:\n\n{diff_text}",
                model=config.model_fix,
                temperature=0.1,
            )
        except Exception as exc:
            logger.error("AI fix failed: %s", exc)
            return 1
        files = _parse_fixes(result or "")
        if not files:
            logger.info("No fixes generated")
            return 0
        written = writer.write_batch(files)
        logger.info("Wrote %d/%d fixed files", written, len(files))

        if args.pr_number:
            break

        exit_code, test_output = _run_tests()
        if exit_code == 0:
            logger.info("Tests pass after fix")
            return 0
        if attempt < retries:
            logger.warning("Tests failed after fix (attempt %d), retrying...", attempt + 1)
            diff_text = f"Previous fix produced:\n{test_output}\n\nOriginal diff:\n{diff_text}"
        attempt += 1

    logger.error("Fix failed after %d attempts", attempt)
    return 1
