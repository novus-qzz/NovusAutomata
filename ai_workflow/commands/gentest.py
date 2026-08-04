"""AI test case generation."""

from __future__ import annotations

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

_SYSTEM_PROMPT = """You are a test engineer. Generate pytest test cases for the following code.
Cover:
1. Normal cases (happy path)
2. Edge cases (empty input, boundary values)
3. Error cases (invalid input, exceptions)

Output format:
===FILE:tests/test_<name>.py===
<test code>
===END===
Only output files that belong in a tests/ directory."""

_FILE_BLOCK = re.compile(r"===FILE:(.+?)===\n(.*?)\n===END===", re.DOTALL)


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the gentest subcommand."""
    parser = subparsers.add_parser("gentest", help="Generate tests")
    parser.add_argument("--source", type=str, default="", help="Optional source file to target")


def run(args: argparse.Namespace, config: Config, ai: AIProvider) -> int:
    """Generate test files from the working-tree diff or a target source."""
    repo = GitRepo()
    if not repo.is_repo():
        logger.error("Not a git repository")
        return 1
    if args.source:
        try:
            with open(args.source, encoding="utf-8") as f:
                source_code = f.read()
        except OSError as exc:
            logger.error("Failed to read source: %s", exc)
            return 1
        context = f"Target source file ({args.source}):\n\n{source_code}"
    else:
        diff_result = repo.diff()
        diff_text = "\n".join(f.content for f in diff_result.files if f.content)
        if not diff_text.strip():
            logger.info("No diff to generate tests for")
            return 0
        context = f"Code changes:\n\n{diff_text}"
    try:
        result = ai.chat(
            _SYSTEM_PROMPT,
            context,
            model=config.model_generic,
            temperature=0.2,
        )
    except Exception as exc:
        logger.error("AI test generation failed: %s", exc)
        return 1
    files: dict[str, str] = {}
    for match in _FILE_BLOCK.finditer(result or ""):
        path = match.group(1).strip()
        if path.startswith("tests/"):
            files[path] = match.group(2)
    if not files:
        logger.warning("AI produced no test files")
        return 1
    writer = SafeFileWriter(config)
    written = writer.write_batch(files)
    logger.info("Generated %d/%d test files", written, len(files))
    return 0 if written > 0 else 1
