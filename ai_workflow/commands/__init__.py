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
    "agent": ("AI 代理：编排多步骤工作流", agent),
    "audit": ("安全审计报告", audit),
    "coverage": ("分析测试覆盖率", coverage),
    "dashboard": ("实时 CI 仪表板", dashboard),
    "deps-audit": ("审计依赖漏洞", deps_audit),
    "diff": ("显示工作区差异摘要", diff),
    "docs": ("生成文档", docs_cmd),
    "explain": ("AI 代码解释", explain),
    "harden": ("安全加固分析", harden),
    "metrics": ("显示代码指标仪表板", metrics),
    "perf": ("分析代码性能", perf),
    "refactor": ("AI 驱动的代码重构", refactor),
    "release": ("自动化发布管理", release),
    "review": ("AI 代码审查", review),
    "describe": ("生成 PR 描述", describe),
    "fix": ("自动修复代码问题", fix),
    "triage": ("问题分类", triage),
    "respond": ("回复问题评论", respond),
    "quality": ("PR 质量门", quality),
    "simplify": ("代码简化建议", simplify),
    "issue2pr": ("将问题转换为 PR", issue2pr),
    "deps": ("审查依赖变更", deps),
    "gentest": ("生成测试", gentest),
    "securix": ("修复安全发现", securix),
    "commitlint": ("验证提交消息", commitlint),
    "health": ("代码健康报告", health),
    "assign": ("建议 PR 审查者", assign),
    "welcome": ("欢迎首次贡献者", welcome),
    "changelog": ("生成变更日志", changelog),
    "summary": ("每周代码摘要", summary),
    "stale": ("管理过期问题/PR", stale),
    "readme": ("同步 README 与代码", readme),
    "plan": ("AI 实现计划", plan),
    "status": ("仓库状态仪表板", status),
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
