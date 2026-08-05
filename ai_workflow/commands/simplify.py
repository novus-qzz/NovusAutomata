"""AI 代码简化建议。"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ai_workflow.git_utils import GitRepo

if TYPE_CHECKING:
    import argparse

    from ai_workflow.config import Config
    from ai_workflow.core import AIProvider
logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a code simplification expert. "
    "Analyze the diff and suggest simplifications:"
    "\n1. Redundant conditions (e.g., `if x == True:`)"
    "\n2. Mergeable loops over the same data"
    "\n3. Custom utilities replaceable by stdlib (e.g., `sorted()`)"
    "\n4. Overly long functions that should be split"
    "\n5. Repeated code blocks that should be extracted"
    "\n6. Complex expressions that could be clearer"
    "\n\nFor each suggestion, provide: file, line number, "
    "current code, simplified version."
)


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the simplify subcommand."""
    subparsers.add_parser("simplify", help="建议代码简化")


def run(args: argparse.Namespace, config: Config, ai: AIProvider) -> int:
    """Analyze the working-tree diff for simplification opportunities."""
    repo = GitRepo()
    if not repo.is_repo():
        logger.error("Not a git repository")
        return 1
    diff_result = repo.diff()
    diff_text = "\n".join(f.content for f in diff_result.files if f.content)
    if not diff_text.strip():
        logger.info("No diff to analyze")
        return 0
    try:
        result = ai.chat(
            _SYSTEM_PROMPT,
            f"Diff:\n\n{diff_text}",
            model=config.model_generic,
            temperature=0.2,
        )
    except Exception as exc:
        logger.error("AI simplify failed: %s", exc)
        return 1
    print(result or "No suggestions generated.")
    return 0
