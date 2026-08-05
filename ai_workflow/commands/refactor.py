"""AI-powered automated code refactoring."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ai_workflow.git_utils import GitRepo

if TYPE_CHECKING:
    import argparse

    from ai_workflow.config import Config
    from ai_workflow.core import AIProvider

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a code refactoring expert.
Analyze the code and suggest safe refactoring improvements.

Refactoring types:
- extract-method: Extract repeated code into functions
- rename: Rename variables/functions/classes for clarity
- simplify: Simplify complex expressions
- remove-dead: Remove unused code
- move: Move code to appropriate locations

Output format (markdown):
## Refactoring Summary
Overview of suggested changes.

## Changes
For each refactoring:
- File: <path>
- Type: <refactoring type>
- Description: <what changed>
- Original: <original code>
- Refactored: <new code>

## Safety Notes
Any risks or considerations.

## Testing
Recommendations for testing the changes."""


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the refactor subcommand."""
    p = subparsers.add_parser("refactor", help="AI-powered code refactoring")
    p.add_argument("--file", help="File to refactor")
    p.add_argument(
        "--type",
        choices=["extract-method", "rename", "simplify", "remove-dead", "move"],
        help="Refactoring type",
    )
    p.add_argument("--old-name", help="Old name for rename refactoring")
    p.add_argument("--new-name", help="New name for rename refactoring")
    p.add_argument("--dry-run", action="store_true", help="Show changes without applying")
    p.add_argument("--pr-number", type=int, help="PR number to refactor")


def run(args: argparse.Namespace, config: Config, ai: AIProvider) -> int:
    """Run AI-powered refactoring."""
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
            logger.info("No diff to refactor for PR #%d", args.pr_number)
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
        logger.error("No code to refactor")
        return 1

    refactoring_type = args.type or "simplify"
    user_prompt = f"""Refactor this code:

Type: {refactoring_type}
Source: {source}

Code:
```
{code}
```

Provide specific refactoring suggestions."""

    try:
        result = ai.chat(
            _SYSTEM_PROMPT,
            user_prompt,
            model=config.model_generic,
            temperature=0.2,
        )
    except Exception as exc:
        logger.error("AI refactoring failed: %s", exc)
        return 1

    if not result or not result.strip():
        logger.error("Empty AI response")
        return 1

    if args.dry_run:
        print("## Refactoring Preview (Dry Run)\n")
        print(result)
    else:
        print("## Refactoring Suggestions\n")
        print(result)
        print("\nTo apply changes, use --dry-run first, then manually apply.")

    return 0
