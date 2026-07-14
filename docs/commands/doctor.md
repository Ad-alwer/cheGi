# chegi doctor

Run a comprehensive health check on your Git project.

## Synopsis

```bash
chegi doctor [OPTIONS]
```

## Description

`chegi doctor` inspects your project across three categories and reports color-coded results:

### 🩺 Health

| Check | What it verifies |
|-------|-----------------|
| Git Installed | Checks if Git is available on the system |
| Git Identity | Verifies `user.name` and `user.email` are configured |
| `.gitignore` | Checks file exists and contains common patterns |
| `.chegi/` Config | Verifies `.chegi/` directory with all config files |

### 🔒 Security

| Check | What it verifies |
|-------|-----------------|
| Staged Sensitive Files | Scans staging area for secrets using `chegi guard` patterns |
| `.env` Tracked | Checks if `.env` files are accidentally tracked by Git |
| Pre-commit Hook | Verifies pre-commit hook is installed and executable |
| Secrets in History | Scans Git history for leaked secrets using `guard history` |

### 📊 Stats

| Check | What it verifies |
|-------|-----------------|
| Total Commits | Counts commits in history |
| Branches | Lists local branches |
| Remote Status | Checks if remotes are configured |
| Contributors | Counts unique contributors |
| Remote Sync | Checks ahead/behind vs upstream |

### Output

Results are color-coded:
- **✓ Green** — Pass
- **⚠ Yellow** — Warning (action recommended)
- **✗ Red** — Fail (action required)
- **→ Dim** — Skipped (not applicable)

Each failing check includes an actionable suggestion.

## Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--path` | `-p` | Path to the project directory | `.` |

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | All checks passed or only warnings |
| `1` | One or more checks failed |

## Examples

Check the current directory:

```bash
chegi doctor
```

Check a specific project:

```bash
chegi doctor -p ~/projects/my-app
```

## See Also

- [guard](guard.md) — scan staged files for sensitive data
- [init](init.md) — initialize `.chegi/` in an existing project
