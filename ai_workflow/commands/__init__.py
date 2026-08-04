"""Command registry that maps CLI names to command modules."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse
    from collections.abc import Callable

from ai_workflow.commands import (
    assign,
    changelog,
    commitlint,
    deps,
    describe,
    fix,
    gentest,
    health,
    issue2pr,
    quality,
    readme,
    respond,
    review,
    securix,
    simplify,
    stale,
    summary,
    triage,
    welcome,
)

_REGISTRY: dict[str, tuple[str, Callable]] = {
    "review": ("AI code review", review),
    "describe": ("Generate PR description", describe),
    "fix": ("Auto-fix code issues", fix),
    "triage": ("Triage an issue", triage),
    "respond": ("Respond to an issue comment", respond),
    "quality": ("PR quality gate", quality),
    "simplify": ("Suggest code simplifications", simplify),
    "issue2pr": ("Convert an issue into a PR", issue2pr),
    "deps": ("Review dependency changes", deps),
    "gentest": ("Generate tests", gentest),
    "securix": ("Fix security findings", securix),
    "commitlint": ("Lint commit messages", commitlint),
    "health": ("Code health report", health),
    "assign": ("Suggest PR reviewers", assign),
    "welcome": ("Welcome first-time contributors", welcome),
    "changelog": ("Generate a changelog", changelog),
    "summary": ("Weekly code summary", summary),
    "stale": ("Manage stale issues/PRs", stale),
    "readme": ("Sync README with code", readme),
}


def register_all(parser: argparse.ArgumentParser) -> None:
    """Register all command subparsers onto the root parser."""
    subparsers = parser.add_subparsers(dest="command", required=True, metavar="command")
    for _name, (_help_text, module) in _REGISTRY.items():
        module.register(subparsers)


def lookup(name: str) -> Callable | None:
    """Return the command module for a name, or None."""
    item = _REGISTRY.get(name)
    return item[1] if item else None
