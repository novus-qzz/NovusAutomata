"""将 GitHub 问题转换为自动修复 PR。"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from ai_workflow.gh_utils import GHClient, GHError
from ai_workflow.git_utils import GitError, GitRepo
from ai_workflow.safe_io import SafeFileWriter

if TYPE_CHECKING:
    import argparse

    from ai_workflow.config import Config
    from ai_workflow.core import AIProvider
logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are an expert programmer. "
    "The user has filed an issue requesting a code change. "
    "Generate the fix. "
    "Output each file change in this exact format:"
    "\n\n===FILE:path/to/file.py==="
    "\n<complete new file content>"
    "\n===END==="
    "\n\nRules:"
    "\n1. Only create/modify files needed for the fix"
    "\n2. Do not touch configuration or protected paths"
    "\n3. Preserve existing imports and type annotations"
    "\n4. Output only files that need to change"
)

_FILE_BLOCK = re.compile(r"===FILE:(.+?)===\n(.*?)\n===END===", re.DOTALL)


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the issue2pr subcommand."""
    parser = subparsers.add_parser("issue2pr", help="将问题转换为 PR")
    parser.add_argument("--issue-number", type=int, required=True, help="问题编号")


def run(args: argparse.Namespace, config: Config, ai: AIProvider) -> int:
    """Create a fix branch and PR from an issue."""
    gh = GHClient()
    repo = GitRepo()
    if not repo.is_repo():
        logger.error("Not a git repository")
        return 1
    try:
        issue = gh.issue_view(args.issue_number)
    except GHError as exc:
        logger.error("Failed to fetch issue: %s", exc)
        return 1
    title = issue.get("title", f"issue #{args.issue_number}")
    body = issue.get("body", "")

    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40]
    branch = f"fix/issue-{args.issue_number}-{slug}" if slug else f"fix/issue-{args.issue_number}"
    try:
        repo.create_branch(branch)
    except GitError as exc:
        logger.error("Failed to create branch: %s", exc)
        return 1
    try:
        result = ai.chat(
            _SYSTEM_PROMPT,
            f"Issue title: {title}\n\nIssue body:\n{body}",
            model=config.model_fix,
            temperature=0.2,
        )
    except Exception as exc:
        logger.error("AI generation failed: %s", exc)
        return 1
    files: dict[str, str] = {}
    for match in _FILE_BLOCK.finditer(result or ""):
        files[match.group(1).strip()] = match.group(2)
    if not files:
        logger.warning("AI produced no file changes; nothing to commit")
        repo.checkout("main")
        return 1
    writer = SafeFileWriter(config)
    written = writer.write_batch(files)
    if written == 0:
        logger.error("No files could be written safely")
        repo.checkout("main")
        return 1
    try:
        repo.commit(f"fix: address issue #{args.issue_number}")
        repo.push("origin", branch)
    except GitError as exc:
        logger.error("Failed to commit/push: %s", exc)
        return 1
    pr_body = (
        f"Auto-generated PR to address issue #{args.issue_number}.\n\n"
        f"{body}\n\nCloses #{args.issue_number}"
    )
    url = gh.pr_create(f"Fix: {title}", pr_body, branch)
    if url:
        gh.issue_comment(args.issue_number, f"Opened PR to address this: {url}")
        logger.info("Created PR for issue #%d: %s", args.issue_number, url)
    return 0
