"""安全加固和漏洞扫描。"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ai_workflow.git_utils import GitRepo

if TYPE_CHECKING:
    import argparse

    from ai_workflow.config import Config
    from ai_workflow.core import AIProvider

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a security hardening expert.
Analyze the code for security vulnerabilities and suggest fixes.

Check for:
- SQL injection
- XSS (Cross-Site Scripting)
- Command injection
- Path traversal
- Hardcoded secrets
- Insecure deserialization
- Missing input validation
- Weak cryptography
- Insecure file operations
- Network security issues

Output format (markdown):
## Security Summary
Overall security assessment (score: 0-100).

## Critical Vulnerabilities
Issues that require immediate attention.

## Security Recommendations
Best practices and hardening suggestions.

## Code Fixes
Before/after examples for critical fixes.

## Security Checklist
Items to verify before deployment."""


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the harden subcommand."""
    p = subparsers.add_parser("harden", help="安全加固分析")
    p.add_argument("--file", help="分析特定文件")
    p.add_argument(
        "--check-dependencies",
        action="store_true",
        help="检查依赖漏洞",
    )
    p.add_argument("--scan-secrets", action="store_true", help="扫描硬编码密钥")
    p.add_argument("--fix", action="store_true", help="建议漏洞修复方案")


def run(args: argparse.Namespace, config: Config, ai: AIProvider) -> int:
    """Run security hardening analysis."""
    code = ""
    source = ""

    if args.file:
        try:
            with open(args.file, encoding="utf-8") as f:
                code = f.read()
            source = args.file
        except OSError as exc:
            logger.error("Failed to read file %s: %s", args.file, exc)
            return 1
    else:
        repo = GitRepo()
        if not repo.is_repo():
            logger.error("Not a git repository")
            return 1
        diff_result = repo.diff()
        code = "\n".join(f.content for f in diff_result.files if f.content)
        source = "working tree"
        if not code.strip():
            logger.info("No changes in the working tree")
            return 0

    if not code.strip():
        logger.error("No code to analyze")
        return 1

    user_prompt = f"""Analyze this code for security vulnerabilities:

Source: {source}

Code:
```
{code}
```

Provide a comprehensive security analysis."""

    try:
        result = ai.chat(
            _SYSTEM_PROMPT,
            user_prompt,
            model=config.model_security,
            temperature=0.1,
        )
    except Exception as exc:
        logger.error("AI security analysis failed: %s", exc)
        return 1

    if not result or not result.strip():
        logger.error("Empty AI response")
        return 1

    print("## Security Hardening Report\n")
    print(result)
    return 0
