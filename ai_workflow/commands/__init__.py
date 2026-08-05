"""Command registry that maps CLI names to command modules."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse
    from collections.abc import Callable

from ai_workflow.commands import (
    agent,
    assign,
    audit,
    changelog,
    commitlint,
    coverage,
    dashboard,
    deps,
    deps_audit,
    describe,
    diff,
    docs_cmd,
    explain,
    fix,
    gentest,
    harden,
    health,
    issue2pr,
    metrics,
    perf,
    plan,
    quality,
    readme,
    refactor,
    release,
    respond,
    review,
    securix,
    simplify,
    stale,
    status,
    summary,
    triage,
    welcome,
)

_REGISTRY: dict[str, tuple[str, Callable]] = {
    "agent": ("AI agent: orchestrate multi-step workflows", agent),
    "audit": ("Security audit from report", audit),
    "coverage": ("Analyze test coverage", coverage),
    "dashboard": ("Real-time CI dashboard", dashboard),
    "deps-audit": ("Audit dependencies for vulnerabilities", deps_audit),
    "diff": ("Show working-tree diff summary", diff),
    "docs": ("Generate documentation", docs_cmd),
    "explain": ("Explain code with AI", explain),
    "harden": ("Security hardening analysis", harden),
    "metrics": ("Show code metrics dashboard", metrics),
    "perf": ("Analyze code performance", perf),
    "refactor": ("AI-powered code refactoring", refactor),
    "release": ("Automated release management", release),
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
    "plan": ("AI plan for upcoming changes", plan),
    "status": ("Repository status dashboard", status),
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
