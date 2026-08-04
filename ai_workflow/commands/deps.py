"""AI dependency change review."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from ai_workflow.core import extract_json
from ai_workflow.git_utils import GitRepo

if TYPE_CHECKING:
    import argparse

    from ai_workflow.config import Config
    from ai_workflow.core import AIProvider
logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a dependency reviewer. Analyze the changed dependency lines.
Check for:
1. Known vulnerabilities in new dependencies
2. Breaking changes in major version bumps
3. License compatibility issues
4. Unnecessary new dependencies
5. Version conflicts

Output a JSON object (no other text):
{
  "safe": true,
  "issues": [
    {"dependency": "<name>", "severity": "high|medium|low", "details": "..."}
  ],
  "recommendation": "approve|review|reject"
}"""

_DEP_PATHS = (
    "requirements.txt",
    "pyproject.toml",
    "package.json",
    "package-lock.json",
    "Pipfile",
    "go.mod",
    "Cargo.toml",
)


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the deps subcommand."""
    subparsers.add_parser("deps", help="Review dependency changes")


def run(args: argparse.Namespace, config: Config, ai: AIProvider) -> int:
    """Analyze dependency changes in the working-tree diff."""
    repo = GitRepo()
    if not repo.is_repo():
        logger.error("Not a git repository")
        return 1
    diff_result = repo.diff()

    def is_dep_path(f: object) -> bool:
        return f.path in _DEP_PATHS or f.path.endswith("lock.json")

    dep_files = [f for f in diff_result.files if is_dep_path(f)]
    if not dep_files:
        logger.info("No dependency changes detected")
        return 0
    diff_text = "\n".join(f.content for f in dep_files if f.content)
    try:
        result = ai.chat(
            _SYSTEM_PROMPT,
            f"Dependency changes:\n\n{diff_text}",
            model=config.model_security,
            temperature=0.0,
        )
    except Exception as exc:
        logger.error("AI deps review failed: %s", exc)
        return 1
    try:
        data = extract_json(result or "{}")
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse deps JSON: %s", exc)
        return 1
    safe = bool(data.get("safe", False))
    recommendation = data.get("recommendation", "review")
    print(f"Safe: {safe} | Recommendation: {recommendation}")
    for issue in data.get("issues", []):
        sev = issue.get("severity", "?")
        dep = issue.get("dependency", "?")
        details = issue.get("details", "")
        print(f"- [{sev}] {dep}: {details}")
    return 0 if safe else 1
