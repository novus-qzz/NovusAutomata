"""Code metrics dashboard with complexity and quality tracking."""

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


def _calculate_cyclomatic_complexity(tree: ast.AST) -> int:
    """Calculate cyclomatic complexity of an AST."""
    complexity = 1
    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
            complexity += 1
        elif isinstance(node, ast.BoolOp):
            complexity += len(node.values) - 1
        elif isinstance(node, (ast.And, ast.Or)):
            complexity += 1
    return complexity


def _calculate_maintainability_index(complexity: int, loc: int) -> float:
    """Calculate maintainability index (simplified)."""
    if loc == 0:
        return 100.0
    volume = loc * 1.0
    mi = max(0.0, 171.0 - 5.2 * (volume ** 0.23) - 16.2 * complexity)
    return float(min(100.0, max(0.0, mi)))


def _analyze_file(file_path: Path) -> dict[str, object]:
    """Analyze a single Python file for metrics."""
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content)
    except (OSError, SyntaxError) as exc:
        logger.warning("Failed to analyze %s: %s", file_path, exc)
        return {}

    loc = len(content.splitlines())
    complexity = _calculate_cyclomatic_complexity(tree)
    maintainability = _calculate_maintainability_index(complexity, loc)

    return {
        "path": str(file_path),
        "lines_of_code": loc,
        "complexity": complexity,
        "maintainability_index": maintainability,
    }


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the metrics subcommand."""
    p = subparsers.add_parser("metrics", help="Show code metrics dashboard")
    p.add_argument("--file", help="Analyze single file")
    p.add_argument("--directory", default="src", help="Directory to analyze")
    p.add_argument("--json", action="store_true", help="Output raw JSON")


def run(args: argparse.Namespace, config: Config, ai: AIProvider) -> int:
    """Analyze code metrics and generate report."""
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            logger.error("File not found: %s", args.file)
            return 1
        metrics = [_analyze_file(file_path)]
    else:
        dir_path = Path(args.directory)
        if not dir_path.exists():
            logger.error("Directory not found: %s", args.directory)
            return 1
        metrics = []
        for py_file in dir_path.rglob("*.py"):
            result = _analyze_file(py_file)
            if result:
                metrics.append(result)

    if not metrics:
        logger.info("No files to analyze")
        return 0

    total_loc = sum(int(m.get("lines_of_code", 0)) for m in metrics)
    avg_complexity = sum(int(m.get("complexity", 0)) for m in metrics) / len(metrics)
    avg_maintainability = sum(
        float(str(m.get("maintainability_index", 0))) for m in metrics
    ) / len(metrics)

    if args.json:
        import json

        print(json.dumps({"files": metrics, "summary": {
            "total_files": len(metrics),
            "total_loc": total_loc,
            "avg_complexity": round(avg_complexity, 2),
            "avg_maintainability": round(avg_maintainability, 2),
        }}, indent=2))
    else:
        print("## Code Metrics Dashboard\n")
        print(f"**Files Analyzed**: {len(metrics)}")
        print(f"**Total Lines**: {total_loc}")
        print(f"**Average Complexity**: {avg_complexity:.2f}")
        print(f"**Average Maintainability**: {avg_maintainability:.2f}\n")
        print("| File | LOC | Complexity | Maintainability |")
        print("|------|-----|------------|-----------------|")
        for m in sorted(metrics, key=lambda x: int(x.get("complexity", 0)), reverse=True):
            path = m.get("path", "")
            loc = m.get("lines_of_code", 0)
            cplx = m.get("complexity", 0)
            mi = m.get("maintainability_index", 0)
            print(f"| {path} | {loc} | {cplx} | {mi} |")

    return 0
