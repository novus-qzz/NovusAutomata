# NovusAutomata - AI Agent Guidelines

## Code Standards
- **Python 3.10+**: Use modern type annotations (`list[int]` not `List[int]`)
- **Docstrings**: Google-style docstrings for all public functions
- **Formatting**: Follow Ruff formatting (`ruff format`)
- **Linting**: All code must pass `ruff check` with strict rules
- **Type Hints**: Strict mypy mode — all functions must have type annotations
- **Testing**: pytest with coverage on new code

## Architecture

```
NovusAutomata/
├── ai_workflow/              # Core AI workflow engine (modular package)
│   ├── __init__.py           # Package init, exports Config
│   ├── __main__.py           # CLI entry point
│   ├── config.py             # Config dataclass with env/file loading
│   ├── core.py               # AIProvider ABC, NVIDIAProvider
│   ├── gh_utils.py           # GitHub API wrapper (gh CLI)
│   ├── git_utils.py          # Git operations wrapper
│   ├── models.py             # Data models (DiffFile, TriageResult, etc.)
│   ├── safe_io.py            # Safe file writer with path validation
│   └── commands/             # 27 command modules
│       ├── __init__.py       # Command registry
│       ├── base.py           # Command infrastructure
│       └── *.py              # Individual commands
├── tests/                    # Test suite
├── .github/workflows/        # 23 CI/CD workflow definitions
├── .githooks/                # Local git hooks
└── pyproject.toml            # Project configuration
```

## Command Catalog

### AI Commands (require NVIDIA API key)

| Command | Description | Trigger |
|---------|-------------|---------|
| `agent` | LLM-driven orchestration (PLAN→EXECUTE→CHECK loop) | Manual |
| `review` | AI PR code review | PR opened/sync |
| `describe` | AI PR description generation | PR opened |
| `fix` | AI auto-fix with test retry loop | PR opened/sync |
| `quality` | Multi-dimensional quality gate scoring | PR opened/sync |
| `triage` | Issue classification and labeling | Issue opened |
| `respond` | AI issue comment response | Issue comment |
| `plan` | AI implementation plan | Manual |
| `gentest` | Test case generation | Manual |
| `simplify` | Code simplification suggestions | Manual |
| `changelog` | AI changelog generation | Tag push |
| `summary` | Weekly code summary | Schedule |
| `assign` | PR reviewer suggestions | PR opened |
| `welcome` | First-time contributor welcome | Issue/PR opened |
| `securix` | Security fix application | Security scan fails |
| `deps` | Dependency change review | PR on dep changes |
| `audit` | Security audit from scanner report | Manual |
| `issue2pr` | Issue-to-PR conversion | Issue labeled |

### Git Commands (no API key required)

| Command | Description | Trigger |
|---------|-------------|---------|
| `diff` | Show working-tree diff summary | Manual |
| `status` | Repository health status | Manual |
| `commitlint` | Validate commit messages | PR opened/sync |
| `stale` | Stale issue management | Schedule |
| `health` | Code health report | Schedule |
| `readme` | README sync | Push to main |

### CI Dashboard

| Command | Description | Trigger |
|---------|-------------|---------|
| `dashboard` | Real-time CI runs table | Manual |

## AI Model Selection

| Task | Model |
|------|-------|
| PR Review / Quality Gate | `deepseek-ai/deepseek-v4-pro` |
| Auto Fix / Daily Tasks | `deepseek-ai/deepseek-v4-flash` |
| Issue Triage / Automation | `nvidia/nemotron-3-super-120b-a12b` |

## Review Criteria
1. All new code must have corresponding tests
2. Type annotations required on all public functions
3. No hardcoded secrets or credentials
4. Follow existing patterns in the codebase
5. Keep functions small and single-purpose

## Workflow Conventions
- Commit messages follow [Conventional Commits](.github/commit-convention.md)
- PRs require AI review + quality gate + CI green
- Dependabot handles dependency updates weekly

## Testing

Run the full test suite:
```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=ai_workflow --cov-report=term-missing

# Run specific test file
python -m pytest tests/test_commands.py -v
```

## Code Quality

Run all quality checks:
```bash
# Linting
python -m ruff check .

# Type checking
python -m mypy ai_workflow/

# Format code
python -m ruff format .
```
