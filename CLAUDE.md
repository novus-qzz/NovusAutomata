# NovusAutomata - AI 代理指南

## 代码规范
- **Python 3.10+**: 使用现代类型注解 (`list[int]` 而非 `List[int]`)
- **文档字符串**: 所有公共函数使用 Google 风格文档字符串
- **格式化**: 遵循 Ruff 格式化 (`ruff format`)
- **代码检查**: 所有代码必须通过 `ruff check` 严格规则
- **类型提示**: 严格 mypy 模式 — 所有函数必须有类型注解
- **测试**: 新代码需要 pytest 测试覆盖率

## 架构

```
NovusAutomata/
├── ai_workflow/              # 核心 AI 工作流引擎（模块化包）
│   ├── __init__.py           # 包初始化，导出 Config
│   ├── __main__.py           # CLI 入口点
│   ├── config.py             # Config 数据类，支持环境变量/文件加载
│   ├── core.py               # AIProvider ABC, NVIDIAProvider
│   ├── gh_utils.py           # GitHub API 封装 (gh CLI)
│   ├── git_utils.py          # Git 操作封装
│   ├── models.py             # 数据模型 (DiffFile, TriageResult 等)
│   ├── safe_io.py            # 安全文件写入器，带路径验证
│   └── commands/             # 34 个命令模块
│       ├── __init__.py       # 命令注册表
│       ├── base.py           # 命令基础设施
│       └── *.py              # 各个命令
├── tests/                    # 测试套件
├── .github/workflows/        # 23 个 CI/CD 工作流定义
├── .githooks/                # 本地 git hooks
└── pyproject.toml            # 项目配置
```

## 命令目录

### AI 命令（需要 NVIDIA API 密钥）

| 命令 | 描述 | 触发方式 |
|------|------|----------|
| `agent` | LLM 驱动的编排（PLAN→EXECUTE→CHECK 循环） | 手动 |
| `review` | AI PR 代码审查 | PR 打开/同步 |
| `describe` | AI PR 描述生成 | PR 打开 |
| `fix` | AI 自动修复，带测试重试循环 | PR 打开/同步 |
| `quality` | 多维度质量门评分 | PR 打开/同步 |
| `triage` | 问题分类和标签 | 问题打开 |
| `respond` | AI 问题评论响应 | 问题评论 |
| `plan` | AI 实现计划 | 手动 |
| `gentest` | 测试用例生成 | 手动 |
| `simplify` | 代码简化建议 | 手动 |
| `changelog` | AI 变更日志生成 | 标签推送 |
| `summary` | 每周代码摘要 | 定时 |
| `assign` | PR 审查者建议 | PR 打开 |
| `welcome` | 欢迎首次贡献者 | 问题/PR 打开 |
| `securix` | 安全修复应用 | 安全扫描失败 |
| `deps` | 依赖变更审查 | PR 依赖变更 |
| `audit` | 安全审计扫描报告 | 手动 |
| `issue2pr` | 问题转 PR 转换 | 问题标签 |
| `explain` | AI 代码解释，支持多级详细程度 | 手动 |
| `perf` | AI 性能瓶颈检测 | 手动 |
| `deps-audit` | 依赖漏洞和许可证审计 | 手动 |
| `metrics` | 代码复杂度和质量指标仪表板 | 手动 |
| `refactor` | AI 驱动的代码重构建议 | 手动 |
| `coverage` | 测试覆盖率分析和建议 | 手动 |
| `release` | 自动版本升级和发布管理 | 手动 |
| `docs` | AI 文档生成 | 手动 |
| `harden` | 安全加固分析 | 手动 |

### Git 命令（无需 API 密钥）

| 命令 | 描述 | 触发方式 |
|------|------|----------|
| `diff` | 显示工作区差异摘要 | 手动 |
| `status` | 仓库健康状态 | 手动 |
| `commitlint` | 验证提交消息 | PR 打开/同步 |
| `stale` | 过期问题管理 | 定时 |
| `health` | 代码健康报告 | 定时 |
| `readme` | README 同步 | 推送到 main |

### CI 仪表板

| 命令 | 描述 | 触发方式 |
|------|------|----------|
| `dashboard` | 实时 CI 运行表格 | 手动 |

## AI 模型选择

| 任务 | 模型 |
|------|------|
| PR 审查 / 质量门 | `deepseek-ai/deepseek-v4-pro` |
| 自动修复 / 日常任务 | `deepseek-ai/deepseek-v4-flash` |
| 问题分类 / 自动化 | `nvidia/nemotron-3-super-120b-a12b` |

## 审查标准
1. 所有新代码必须有对应的测试
2. 所有公共函数必须有类型注解
3. 不得硬编码密钥或凭证
4. 遵循代码库中的现有模式
5. 保持函数小而单一职责

## 工作流约定
- 提交消息遵循 [常规提交规范](.github/commit-convention.md)
- PR 需要 AI 审查 + 质量门 + CI 绿灯
- Dependabot 每周处理依赖更新

## 测试

运行完整测试套件：
```bash
# 运行所有测试
python -m pytest tests/ -v

# 带覆盖率运行
python -m pytest tests/ --cov=ai_workflow --cov-report=term-missing

# 运行特定测试文件
python -m pytest tests/test_commands.py -v
```

## 代码质量

运行所有质量检查：
```bash
# 代码检查
python -m ruff check .

# 类型检查
python -m mypy ai_workflow/

# 格式化代码
python -m ruff format .
```
