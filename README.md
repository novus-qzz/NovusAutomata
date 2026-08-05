# NovusAutomata

**AI-powered Git workflow automation** — a modular CLI toolkit that automates code review, issue triage, auto-fixing, changelog generation, and more via NVIDIA NIM AI.

## Features

- **19 modular commands** — review, fix, triage, quality, changelog, health, and more
- **22 GitHub Actions workflows** — CI, PR automation, issue management, security, community
- **Local Git hooks** — pre-commit, commit-msg, post-commit
- **Safe file I/O** — path traversal protection, atomic writes, protected path whitelist
- **Strict quality** — ruff + mypy strict + pytest

## Quick Start

```bash
# Clone and install
pip install -e .

# Set NVIDIA API key
export NVIDIA_API_KEY=your-key

# Run a command
ai-workflow review --pr-number 123
ai-workflow triage --issue-number 456
ai-workflow fix --pr-number 123
```

## Commands

| Command | Description |
|---------|-------------|
| `review` | AI code review of a PR |
| `describe` | Generate a PR description |
| `fix` | Auto-fix code issues |
| `triage` | Triage an issue |
| `respond` | Respond to an issue comment |
| `quality` | PR quality gate scoring |
| `simplify` | Suggest code simplifications |
| `issue2pr` | Convert an issue into a PR |
| `deps` | Review dependency changes |
| `gentest` | Generate test cases |
| `securix` | Fix security findings |
| `commitlint` | Lint commit messages |
| `health` | Code health report |
| `assign` | Suggest PR reviewers |
| `welcome` | Welcome first-time contributors |
| `changelog` | Generate a changelog |
| `summary` | Weekly code summary |
| `stale` | Manage stale issues/PRs |
| `readme` | Sync README with code |

## CI/CD Workflows

- **01 CI**: Adaptive lint & test (auto-detect language)
- **02 Lint**: reviewdog static analysis
- **03-05, 09-10, 21**: PR automation (review, description, auto-fix, quality gate)
- **06-08, 22**: Issue automation (triage, issue-to-PR, response, welcome)
- **11 Security**: gitleaks + bandit + pip-audit
- **12-20**: Metadata, code health, stale management
- **21-22**: Community management

## Requirements

- Python 3.10+
- NVIDIA NIM API key
- GitHub CLI (`gh`) for GitHub operations

## License

MIT
