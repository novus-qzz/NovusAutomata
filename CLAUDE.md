# NovusAutomata - AI Agent Guidelines

## Code Standards
- **Python 3.10+**: Use modern type annotations (`list[int]` not `List[int]`)
- **Docstrings**: Google-style docstrings for all public functions
- **Formatting**: Follow Ruff formatting (`ruff format`)
- **Linting**: All code must pass `ruff check` with strict rules
- **Type Hints**: Strict mypy mode — all functions must have type annotations
- **Testing**: pytest with coverage on new code

## Architecture
- `app.py` — Core business logic functions
- `tests/test_app.py` — Corresponding test file
- `ai_workflow/` — Core AI workflow engine (modular package)
- `.github/workflows/` — CI/CD pipeline definitions
- `.githooks/` — Local git hooks (pre-commit, commit-msg, post-commit)

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
