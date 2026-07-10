# chegi reword

Reword a Git commit message interactively.

## Synopsis

```bash
chegi reword [MESSAGE] [OPTIONS]
```

## Description

`chegi reword` lets you change a commit message in the current repository. By default it rewords the latest commit (`HEAD`). Use pagination options to pick an older commit from an interactive menu.

- **HEAD commit** — uses `git commit --amend`
- **Older commits** — uses an automated interactive rebase

## Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `MESSAGE` | New commit message (skips the interactive prompt) | prompted interactively |

## Options

| Option | Short | Description |
|--------|-------|-------------|
| `--last` | `-l` | Show the last N commits to choose from (max `20`) |
| `--start` | `-s` | Start index for the commit list |
| `--end` | `-e` | End index for the commit list |

### Pagination Rules

| Flags | Behavior |
|-------|----------|
| `--last 5` | Show the 5 most recent commits |
| `--start 2 --end 12` | Show commits from index 2 to 12 |
| `--start 5` | Show 10 commits starting at index 5 |
| `--end 8` | Show up to 10 commits ending at index 8 |

`--start` must be less than `--end` when both are provided.

## Examples

Reword the latest commit (interactive message prompt):

```bash
chegi reword
```

Reword HEAD with a new message directly:

```bash
chegi reword "fix: correct login redirect"
```

Pick from the last 10 commits:

```bash
chegi reword --last 10
```

Pick a commit from a specific range:

```bash
chegi reword --start 0 --end 15
```

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success, or message unchanged, or user cancelled selection |
| `1` | Git error, invalid range, empty message, or `--last` exceeds 20 |

## See Also

- [sync](sync.md) — sync after rewriting history (may require force-push for older commits)
