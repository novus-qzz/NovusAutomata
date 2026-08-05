"""依赖审计仪表板，支持漏洞和许可证跟踪。"""

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

_SYSTEM_PROMPT = """You are a dependency security expert.
Analyze the dependency information and provide a comprehensive audit.

Output format (markdown):
## Dependency Audit Summary
Total dependencies, vulnerabilities found, license issues.

## Vulnerability Details
Table of vulnerabilities with:
- Package name
- Current version
- Vulnerability ID (CVE)
- Severity (Critical/High/Medium/Low)
- Description
- Recommended fix

## License Compliance
List of licenses found and any compliance issues.

## Outdated Packages
Packages that need updating with version comparison.

## Recommendations
Priority actions to improve dependency security."""


def _parse_requirements(file_path: str) -> list[dict[str, str]]:
    """Parse requirements file and extract package info."""
    packages = []
    try:
        with open(file_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                if "==" in line:
                    name, version = line.split("==", 1)
                    packages.append({"name": name.strip(), "version": version.strip()})
                elif ">=" in line:
                    name, version = line.split(">=", 1)
                    packages.append({"name": name.strip(), "version": f">={version.strip()}"})
                else:
                    packages.append({"name": line, "version": "latest"})
    except OSError as exc:
        logger.error("Failed to read requirements file: %s", exc)
    return packages


def _run_pip_audit() -> dict[str, object]:
    """Run pip-audit and return results."""
    try:
        result = subprocess.run(
            ["pip-audit", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if result.returncode == 0:
            data: dict[str, object] = json.loads(result.stdout)
            return data
        logger.warning("pip-audit returned non-zero exit code: %d", result.returncode)
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        logger.warning("pip-audit failed: %s", exc)
    return {"dependencies": []}


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the deps-audit subcommand."""
    p = subparsers.add_parser("deps-audit", help="审计依赖漏洞")
    p.add_argument("--file", default="requirements.txt", help="要审计的依赖文件")
    p.add_argument("--check-licenses", action="store_true", help="检查许可证合规性")
    p.add_argument("--json", action="store_true", help="输出原始 JSON")


def run(args: argparse.Namespace, config: Config, ai: AIProvider) -> int:
    """Run dependency audit and generate report."""
    packages = _parse_requirements(args.file)
    if not packages:
        logger.info("No packages found in %s", args.file)
        return 0

    audit_data = _run_pip_audit()
    vulnerabilities = audit_data.get("dependencies", [])

    user_prompt = f"""Analyze these dependencies:

Packages found ({len(packages)}):
{json.dumps(packages, indent=2)}

Vulnerabilities from pip-audit:
{json.dumps(vulnerabilities, indent=2)}

Provide a comprehensive dependency audit report."""

    try:
        result = ai.chat(
            _SYSTEM_PROMPT,
            user_prompt,
            model=config.model_security,
            temperature=0.1,
        )
    except Exception as exc:
        logger.error("AI dependency audit failed: %s", exc)
        return 1

    if args.json:
        print(json.dumps({"packages": packages, "vulnerabilities": vulnerabilities}, indent=2))
    else:
        print("## Dependency Audit Report\n")
        print(result or "No issues found.")

    return 0
