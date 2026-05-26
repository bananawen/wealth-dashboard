# Conventional Commits Guide

## Format

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

## Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Code style (formatting, no logic change) |
| `refactor` | Code refactoring (no feature/fix) |
| `perf` | Performance improvement |
| `test` | Adding/updating tests |
| `build` | Build system or dependency change |
| `ci` | CI configuration |
| `chore` | Other changes (maintenance, deps) |
| `revert` | Revert previous commit |

## Examples

```bash
# Feature
git commit -m "feat(auth): add JWT token refresh"

# Bug fix
git commit -m "fix(portfolio): correct XIRR calculation for negative returns"

# Documentation
git commit -m "docs: update README with new API endpoints"

# Refactoring
git commit -m "refactor(scraper): extract base fetcher class"

# With body
git commit -m "feat(ui): add dark mode toggle

- Add ThemeContext provider
- Implement CSS variables for colors
- Update all components to use theme classes"
```

## Scope (optional)

Common scopes:
- `auth` - Authentication
- `api` - API routes
- `ui` - User interface
- `scraper` - Stock scrapers
- `db` - Database
- `config` - Configuration

## Rules

1. Subject line ≤ 72 characters
2. Use imperative mood ("add" not "added")
3. Don't end with period
4. Reference issues: `Closes #123`, `Fixes #456`