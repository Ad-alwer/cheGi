# `chegi info`

Quick project status overview — branch, changes, sync, security, and more.

## Synopsis

```bash
chegi info [OPTIONS]
```

## Description

`chegi info` displays a Rich dashboard with your project's current state at a
glance. It shows information from Git, Guard, Hooks, and project configuration
in a single compact view.

### Dashboard Sections

1. **Branch & Sync** — current branch, remote URL, ahead/behind count
2. **Changes** — staged, modified, untracked files; stash count
3. **Commit** — last commit hash, message, author, relative date; contributor count
4. **Security & Config** — guard scan result, hook status, git identity, `.chegi/` setup

## Options

| Option | Short | Description |
|--------|-------|-------------|
| `--short` | `-s` | One-line summary |
| `--json` | `-j` | JSON output (machine-readable) |
| `--watch` | `-w` | Live refresh every 2 seconds |
| `--path` | `-p` | Target project directory |

## Examples

```bash
# Full dashboard
chegi info

# One-line summary
chegi info -s

# JSON for scripting
chegi info -j | jq '.branch'

# Live refresh
chegi info -w

# Check another directory
chegi info -p ../other-project

# Combined: JSON from another directory
chegi info -p ~/work/project -j
```

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success (or JSON/short output even if issues found) |
| `1` | Dashboard mode with errors (non-git repo, guard issues) |
