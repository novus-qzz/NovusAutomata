"""Command module infrastructure.

Each command module exposes:
    - ``register(subparsers)``: attach argparse arguments.
    - ``run(args, config, ai)``: execute and return an exit code.

The ``BaseCommand`` helper wires common arguments (``--pr-number``,
``--issue-number``, etc.) and standard logging.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import argparse

    from ai_workflow.config import Config
    from ai_workflow.core import AIProvider


class Command(Protocol):
    """Structural protocol for a command module."""

    def register(self, subparsers: argparse._SubParsersAction) -> None:
        """Register subcommand arguments with argparse."""

    def run(self, args: argparse.Namespace, config: Config, ai: AIProvider) -> int:
        """Execute the command and return an exit code."""


def setup_logging(config: Config) -> None:
    """Configure root logging from config."""
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper(), logging.INFO),
        format=config.log_format,
    )
