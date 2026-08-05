"""测试覆盖率分析与建议。"""

from __future__ import annotations

import json
import logging
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse

    from ai_workflow.config import Config
    from ai_workflow.core import AIProvider

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a test coverage expert.
Analyze the coverage data and suggest improvements.

Output format (markdown):
## Coverage Summary
Overall coverage percentage and metrics.

## Uncovered Code
List of files/functions with low coverage.

## Suggested Tests
For each uncovered area:
- Function/method to test
- Test scenarios (happy path, edge cases, error cases)
- Expected assertions

## Coverage Trends
If historical data available, show improvement/degradation.

## Recommendations
Priority actions to improve coverage."""


def _run_coverage() -> dict[str, object]:
    """Run pytest with coverage and return results."""
    try:
        subprocess.run(
            ["python", "-m", "pytest", "--cov=ai_workflow", "--cov-report=json", "-q"],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        try:
            with open("coverage.json", encoding="utf-8") as f:
                data: dict[str, object] = json.load(f)
                return data
        except FileNotFoundError:
            logger.warning("Coverage report not generated")
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        logger.warning("Coverage analysis failed: %s", exc)
    return {}


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the coverage subcommand."""
    p = subparsers.add_parser("coverage", help="分析测试覆盖率")
    p.add_argument("--file", help="分析特定文件的覆盖率")
    p.add_argument("--directory", help="分析目录的覆盖率")
    p.add_argument("--suggest-tests", action="store_true", help="为未覆盖代码建议测试")
    p.add_argument("--json", action="store_true", help="输出原始 JSON")


def run(args: argparse.Namespace, config: Config, ai: AIProvider) -> int:
    """Analyze test coverage and generate report."""
    coverage_data = _run_coverage()

    if not coverage_data:
        logger.info("No coverage data available. Run pytest with --cov first.")
        return 0

    files = coverage_data.get("files", {})
    total = coverage_data.get("totals", {})

    if args.json:
        print(json.dumps(coverage_data, indent=2))
        return 0

    print("## Test Coverage Report\n")
    print(f"**Total Coverage**: {total.get('percent_covered', 0):.1f}%")
    print(f"**Covered Lines**: {total.get('covered_lines', 0)}")
    print(f"**Missing Lines**: {total.get('missing_lines', 0)}\n")

    if files:
        print("| File | Coverage | Missing Lines |")
        print("|------|----------|---------------|")
        for path, data in sorted(files.items(), key=lambda x: x[1].get("percent_covered", 0)):
            pct = data.get("percent_covered", 0)
            missing = data.get("missing_lines", 0)
            print(f"| {path} | {pct:.1f}% | {missing} |")

    if args.suggest_tests and ai:
        uncovered = [
            {"file": path, "missing": data.get("missing_lines", 0)}
            for path, data in files.items()
            if data.get("percent_covered", 100) < 80
        ]
        if uncovered:
            user_prompt = f"""Suggest tests for these uncovered areas:

{json.dumps(uncovered, indent=2)}

Provide specific test suggestions."""

            try:
                result = ai.chat(
                    _SYSTEM_PROMPT,
                    user_prompt,
                    model=config.model_generic,
                    temperature=0.3,
                )
                if result:
                    print("\n## Suggested Tests\n")
                    print(result)
            except Exception as exc:
                logger.warning("AI test suggestion failed: %s", exc)

    return 0
