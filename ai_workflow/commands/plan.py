"""AI 辅助的变更计划。"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse

    from ai_workflow.config import Config
    from ai_workflow.core import AIProvider


from ai_workflow.git_utils import GitRepo

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a software architect. Given the current codebase and the user's goal, "
    "produce a step-by-step implementation plan. Include: file changes, function "
    "signatures, key considerations, and estimated effort. "
    "Output as a markdown checklist."
)


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the plan subcommand."""
    p = subparsers.add_parser("plan", help="AI 变更计划")
    p.add_argument("--goal", default="", help="描述您想要构建的内容")


def run(args: argparse.Namespace, config: Config, ai: AIProvider) -> int:
    """Generate an AI implementation plan."""
    repo = GitRepo()
    if not repo.is_repo():
        logger.error("Not a git repository")
        return 1
    goal = getattr(args, "goal", "") or ""
    if not goal:
        logger.warning("No --goal provided; showing diff context")
        result = repo.diff()
        if result.is_empty():
            logger.info("No diff to base a plan on. Use --goal to describe your intent.")
            return 1
        context = "\n".join(f.content for f in result.files if f.content)
    else:
        context = goal
    try:
        plan_text = ai.chat(
            _SYSTEM_PROMPT,
            f"Goal: {context}",
            model=config.model_generic,
            temperature=0.3,
        )
    except Exception as exc:
        logger.error("AI plan failed: %s", exc)
        return 1
    print(plan_text or "No plan generated.")
    return 0
