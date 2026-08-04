# Conventional Commits

## Format

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

## Types

| Type       | Description                          |
| ---------- | ------------------------------------ |
| `feat`     | New feature                          |
| `fix`      | Bug fix                              |
| `chore`    | Maintenance tasks                    |
| `docs`     | Documentation changes                |
| `refactor` | Code restructuring (no behavior change) |
| `test`     | Adding or updating tests              |
| `style`    | Formatting changes (no logic change)  |
| `perf`     | Performance improvements             |
| `ci`       | CI/CD configuration changes          |
| `build`    | Build system changes                 |
| `revert`   | Revert a previous commit             |

## Rules

- Subject is lowercase, imperative mood, no trailing period.
- Subject max 72 characters.
- Optional scope in parentheses (e.g., `feat(api):`).
- Breaking changes: append `!` (e.g., `feat!: drop v1 API`) or add a `BREAKING CHANGE:` footer.

## Examples

```
feat(api): add health check endpoint
fix(auth): handle expired tokens gracefully
docs: update installation instructions
refactor(core): simplify provider abstraction
test: add coverage for safe_io edge cases
```
