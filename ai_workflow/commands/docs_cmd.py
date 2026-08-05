"""AI-powered documentation generation."""

from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse

    from ai_workflow.config import Config
    from ai_workflow.core import AIProvider

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a technical documentation expert.
Generate comprehensive documentation for the code.

Output format (markdown):
## Overview
Brief description of what the module/file does.

## Classes and Functions
For each class/function:
- Name and signature
- Purpose
- Parameters with types
- Return value
- Usage examples

## Usage Examples
Common usage patterns.

## API Reference
Detailed API documentation.

## Notes
Important considerations, limitations, or best practices."""


def _extract_docstrings(file_path: Path) -> dict[str, str]:
    """Extract docstrings from Python file."""
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content)
    except (OSError, SyntaxError) as exc:
        logger.warning("Failed to parse %s: %s", file_path, exc)
        return {}

    docstrings = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            docstring = ast.get_docstring(node)
            if docstring:
                docstrings[node.name] = docstring
    return docstrings


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the docs subcommand."""
    p = subparsers.add_parser("docs", help="Generate documentation")
    p.add_argument("--file", help="Generate docs for specific file")
    p.add_argument("--directory", default="src", help="Generate docs for directory")
    p.add_argument("--readme", action="store_true", help="Update README with code docs")
    p.add_argument("--api-docs", action="store_true", help="Generate API documentation")
    p.add_argument("--dry-run", action="store_true", help="Preview without writing")


def run(args: argparse.Namespace, config: Config, ai: AIProvider) -> int:
    """Generate documentation for code."""
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            logger.error("File not found: %s", args.file)
            return 1
        docstrings = _extract_docstrings(file_path)
        content = file_path.read_text(encoding="utf-8")
        source = args.file
    else:
        dir_path = Path(args.directory)
        if not dir_path.exists():
            logger.error("Directory not found: %s", args.directory)
            return 1
        docstrings = {}
        for py_file in dir_path.rglob("*.py"):
            docstrings.update(_extract_docstrings(py_file))
        content = "\n".join(f"--- {p} ---\n{p.read_text(encoding='utf-8')}"
                           for p in list(dir_path.rglob("*.py"))[:5])
        source = args.directory

    if not docstrings and not content.strip():
        logger.info("No code to document")
        return 0

    user_prompt = f"""Generate documentation for this code:

Source: {source}

Existing docstrings:
{chr(10).join(f'{k}: {v}' for k, v in docstrings.items()) if docstrings else 'None'}

Code preview:
```
{content[:3000]}
```"""

    try:
        result = ai.chat(
            _SYSTEM_PROMPT,
            user_prompt,
            model=config.model_generic,
            temperature=0.3,
        )
    except Exception as exc:
        logger.error("AI documentation generation failed: %s", exc)
        return 1

    if not result or not result.strip():
        logger.error("Empty AI response")
        return 1

    if args.dry_run:
        print("## Documentation Preview (Dry Run)\n")
        print(result)
    else:
        output_file = Path("DOCS.md")
        output_file.write_text(result, encoding="utf-8")
        print(f"Generated documentation: {output_file}")

    return 0
