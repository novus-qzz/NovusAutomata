"""AI code health report."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ai_workflow.git_utils import GitRepo

if TYPE_CHECKING:
    import argparse

    from ai_workflow.config import Config
    from ai_workflow.core import AIProvider
logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a project health analyst. Given the repository metrics below,
generate a code health report covering:
1. Code complexity trends
2. Test coverage signals
3. Dependency age
4. Open issues/PRs and their age
5. Technical debt assessment
6. Recommended focus areas

Format as markdown with clear sections and a final health score (0-100)."""


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the health subcommand."""
    subparsers.add_parser("health", help="Generate a code health report")


def run(args: argparse.Namespace, config: Config, ai: AIProvider) -> int:
    """Analyze repository metrics and generate a health report."""
    repo = GitRepo()
    if not repo.is_repo():
        logger.error("Not a git repository")
        return 1
    commits = repo.log(max_count=50)
    total_commits = len(commits)
    recent = [c for c in commits if c.message]
    try:
        contributors = len({c.author for c in recent})
    except Exception:
        contributors = 0
    context = (
        f"Commits (last 50): {total_commits}\n"
        f"Contributors (last 50): {contributors}\n"
        f"Recent commit types: "
    )
    types: dict[str, int] = {}
    for c in recent:
        first = c.message.split(":")[0].split("(")[0].strip()
        types[first] = types.get(first, 0) + 1
    type_counts = ", ".join(f"{k}={v}" for k, v in sorted(types.items(), key=lambda x: -x[1]))
    context += type_counts or "none"
    try:
        result = ai.chat(
            _SYSTEM_PROMPT,
            context,
            model=config.model_security,
            temperature=0.3,
        )
    except Exception as exc:
        logger.error("AI health report failed: %s", exc)
        return 1
    print(result or "No report generated.")
    return 0
