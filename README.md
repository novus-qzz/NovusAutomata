# NovusAutomata

**AI 驱动的 Git 工作流自动化** — 一个模块化 CLI 工具包，通过 NVIDIA NIM AI 自动化代码审查、问题分类、自动修复、变更日志生成等功能。

## 功能特点

- **34 个模块化命令** — review、fix、triage、quality、changelog、health 等
- **23 个 GitHub Actions 工作流** — CI、PR 自动化、问题管理、安全、社区
- **本地 Git hooks** — pre-commit、commit-msg、post-commit
- **安全文件 I/O** — 路径遍历保护、原子写入、受保护路径白名单
- **严格质量控制** — ruff + mypy strict + pytest

## 快速开始

```bash
# 克隆并安装
pip install -e .

# 设置 NVIDIA API 密钥
export NVIDIA_API_KEY=your-key

# 运行命令
ai-workflow review --pr-number 123
ai-workflow triage --issue-number 456
ai-workflow fix --pr-number 123
```

## 命令列表

| 命令 | 描述 |
|------|------|
| `review` | AI 代码审查 PR |
| `describe` | 生成 PR 描述 |
| `fix` | 自动修复代码问题 |
| `triage` | 问题分类 |
| `respond` | 回复问题评论 |
| `quality` | PR 质量门评分 |
| `simplify` | 代码简化建议 |
| `issue2pr` | 将问题转换为 PR |
| `deps` | 审查依赖变更 |
| `gentest` | 生成测试用例 |
| `securix` | 修复安全发现 |
| `commitlint` | 验证提交消息 |
| `health` | 代码健康报告 |
| `assign` | 建议 PR 审查者 |
| `welcome` | 欢迎首次贡献者 |
| `changelog` | 生成变更日志 |
| `summary` | 每周代码摘要 |
| `stale` | 管理过期问题/PR |
| `readme` | 同步 README 与代码 |
| `explain` | AI 代码解释 |
| `perf` | 性能分析 |
| `deps-audit` | 依赖审计 |
| `metrics` | 代码指标仪表板 |
| `refactor` | AI 自动重构 |
| `coverage` | 测试覆盖率分析 |
| `release` | 发布自动化 |
| `docs` | 文档生成 |
| `harden` | 安全加固分析 |
| `agent` | AI 代理编排 |
| `dashboard` | 实时 CI 仪表板 |
| `diff` | 显示工作区差异摘要 |
| `status` | 仓库健康状态 |
| `plan` | AI 实现计划 |

## CI/CD 工作流

- **01 CI**: 自适应 lint 和测试（自动检测语言）
- **02 Lint**: reviewdog 静态分析
- **03-05, 09-10, 21**: PR 自动化（审查、描述、自动修复、质量门）
- **06-08, 22**: 问题自动化（分类、问题转 PR、响应、欢迎）
- **11 安全**: gitleaks + bandit + pip-audit
- **12-20**: 元数据、代码健康、过期管理
- **21-22**: 社区管理

## 系统要求

- Python 3.10+
- NVIDIA NIM API 密钥
- GitHub CLI (`gh`) 用于 GitHub 操作

## 许可证

MIT
