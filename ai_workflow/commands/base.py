"""Command module infrastructure.

Each command module exposes:
    - ``register(subparsers)``: attach argparse arguments.
    - ``run(args, config, ai)``: execute and return an exit code.

The ``BaseCommand`` helper wires common arguments (``--pr-number``,
``--issue-number``, etc.) and standard logging.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai_workflow.config import Config


def setup_logging(config: Config) -> None:
    """Configure root logging from config."""
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper(), logging.INFO),
        format=config.log_format,
    )
