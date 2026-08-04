"""Main entry point for the NovusAutomata AI workflow CLI.

Usage:
    python -m ai_workflow <command> [options]

Commands:
    review      AI code review of a PR
    describe    Generate a PR description
    fix         Auto-fix code issues
    triage      Triage an issue
    respond     Respond to an issue comment
    quality     PR quality gate
    simplify    Suggest code simplifications
    issue2pr    Convert an issue into a PR
    deps        Review dependency changes
    gentest     Generate tests
    securix     Fix security findings
    commitlint  Lint commit messages
    health      Code health report
    assign      Suggest PR reviewers
    welcome     Welcome first-time contributors
    changelog   Generate a changelog
    summary     Weekly code summary
    stale       Manage stale issues/PRs
    readme      Sync README with code
"""

from __future__ import annotations

import argparse
import logging
import sys

from ai_workflow.commands import register_all
from ai_workflow.commands.base import setup_logging
from ai_workflow.config import load_config
from ai_workflow.core import NVIDIAProvider

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Build the root argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="ai-workflow",
        description="AI-powered Git workflow automation (NovusAutomata).",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 0.2.0")
    register_all(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    config = load_config()
    setup_logging(config)

    command_module = args.command
    try:
        provider = NVIDIAProvider(config)
        module = sys.modules.get(f"ai_workflow.commands.{command_module}")
        if module is None:
            raise RuntimeError(f"Command module not found: {command_module}")
        return int(module.run(args, config, provider))
    except Exception as exc:
        logger.error("%s failed: %s", command_module, exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
