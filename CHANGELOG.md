## HEAD

# Changelog

## Features
- Add unified AI workflow and enable AI configuration
- Add 9 new AI-powered commands
- Add AI agent orchestrator + CI dashboard
- Upgrade to v2 — docs, actions v6, 4 new commands, tests
- NovusAutomata v2 — modular AI Git workflow
- Add 6 new AI workflows + dependabot + CODEOWNERS
- Complete NovusAutomata AI workflow suite
- Add NVIDIA NIM as fallback AI provider with provider chain
- AI fix evolver — 控制论进化器集成到CI
- 项目中文化 + 清理缓存 + ruff 规则优化

## Bug Fixes
- Fix double prefix bug (deepseek-ai/minimaxai/minimax-m3) + ruff exclude evolver/memory
- Fix ai-main.yml deps-audit (was nonexistent version command)
- Replace deprecated NVIDIA models with available ones
- Fix CI workflows - toml dependency, checkout@v4->v6, sync all workflows from main
- Replace hashFiles with always() in security scan workflow
- Upgrade gitleaks-action to v3 (Node 24) and checkout to v6
- Suppress bandit B310 false positive for NVIDIA API call
- Fix 7 review issues + add deps/issue2pr commands
- Increase fetch retry delay to 8s and push_verified wait to 5s
- Fix greet says Goodbye
- Fix add uses subtraction
- Fix multiply subtracts
- Fix add returns second arg
- Fix multiply adds

## Refactoring
- Optimize repository — dead code cleanup, type ignore fixes, docs update, test coverage

## Documentation
- Update CHANGELOG [NovusAutomata]

## Maintenance
- Remove all CI workflows and unused files
- Reset to clean slate
- Restore clean base after 100-iteration test
- Restore clean base
- AI auto-fix [NovusAutomata]

# Changelog

## HEAD

## Features

- **NovusAutomata v2** — Modular AI Git workflow with 9 new AI-powered commands, AI agent orchestrator, and CI dashboard
- **AI Fix Evolver** — Cybernetic evolution integration into CI with unified AI workflow and AI config support
- **NVIDIA NIM fallback** — Added as fallback AI provider with provider chain support
- **6 new AI workflows** — Added dependabot and CODEOWNERS configuration
- **Project localization** — Chinese language support, cache cleanup, and ruff rule optimization
- **4 new commands** — Added deps/issue2pr commands and upgraded to v2 with docs and actions v6

## Bug Fixes

- Replaced deprecated NVIDIA models with available ones
- Fixed CI workflows — toml dependency, checkout@v4→v6, synced all workflows from main
- Replaced `hashFiles()` with `always()` in security scan workflow
- Upgraded gitleaks-action to v3 (Node 24) and checkout to v6
- Suppressed bandit B310 false positive for NVIDIA API call
- Fixed 7 review issues
- Increased fetch retry delay to 8s and push_verified wait to 5s
- Fixed arithmetic bugs in add/multiply functions and greeting message

## Refactoring

- Optimized repository — dead code cleanup, type ignore fixes, docs update, test coverage

## Maintenance

- Removed all CI workflows and unused files
- Reset to clean slate and restored clean base after testing iterations
- AI auto-fix commits from NovusAutomata
