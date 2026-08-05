"""AI 性能分析和瓶颈检测。"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ai_workflow.git_utils import GitRepo

if TYPE_CHECKING:
    import argparse

    from ai_workflow.config import Config
    from ai_workflow.core import AIProvider

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a performance optimization expert.
Analyze the provided code for performance issues.

Identify and categorize issues by type:
- Algorithm: Inefficient algorithms, unnecessary iterations
- Memory: Memory leaks, excessive allocations, large data structures
- I/O: Blocking operations, unnecessary file/network access
- Concurrency: Thread safety, GIL issues, async opportunities
- Caching: Missing caching opportunities, cache invalidation

Output format (markdown):
## Performance Summary
Overall performance assessment (score: 0-100).

## Critical Issues
Issues that significantly impact performance.

## Optimization Opportunities
Suggestions for improvement with expected impact.

## Code Examples
Before/after examples for key optimizations.

## Metrics
- Time complexity analysis
- Memory usage estimation
- Potential speedup factors"""


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the perf subcommand."""
    p = subparsers.add_parser("perf", help="分析代码性能")
    p.add_argument("--file", help="要分析的文件路径")
    p.add_argument("--pr-number", type=int, help="要分析的 PR 编号")
    p.add_argument("--diff", action="store_true", help="分析工作区差异")


def run(args: argparse.Namespace, config: Config, ai: AIProvider) -> int:
    """Analyze code for performance issues."""
    code = ""
    source = ""

    if args.file:
        try:
            with open(args.file, encoding="utf-8") as f:
                code = f.read()
            source = args.file
        except OSError as exc:
            logger.error("Failed to read file %s: %s", args.file, exc)
            return 1
    elif args.pr_number:
        from ai_workflow.gh_utils import GHClient, GHError

        gh = GHClient()
        try:
            diff = gh.pr_diff(args.pr_number)
        except GHError as exc:
            logger.error("Failed to fetch PR diff: %s", exc)
            return 1
        if not diff.strip():
            logger.info("No diff to analyze for PR #%d", args.pr_number)
            return 0
        code = diff
        source = f"PR #{args.pr_number}"
    else:
        repo = GitRepo()
        if not repo.is_repo():
            logger.error("Not a git repository")
            return 1
        diff_result = repo.diff()
        code = "\n".join(f.content for f in diff_result.files if f.content)
        source = "working tree"
        if not code.strip():
            logger.info("No changes in the working tree")
            return 0

    if not code.strip():
        logger.error("No code to analyze")
        return 1

    user_prompt = (
        f"Analyze this code for performance issues:\n\n"
        f"Source: {source}\n\n"
        f"Code:\n```\n{code}\n```"
    )

    try:
        result = ai.chat(
            _SYSTEM_PROMPT,
            user_prompt,
            model=config.model_generic,
            temperature=0.2,
        )
    except Exception as exc:
        logger.error("AI performance analysis failed: %s", exc)
        return 1

    if not result or not result.strip():
        logger.error("Empty AI response")
        return 1

    print("## Performance Analysis Report\n")
    print(result)
    return 0
