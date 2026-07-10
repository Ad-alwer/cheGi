# chegi scan

Scan a directory tree for Git repositories and display a unified status overview.

## Synopsis

```bash
chegi scan [PATH] [OPTIONS]
```

## Description

`chegi scan` walks a directory recursively, discovers Git repositories, and analyzes them concurrently. For each repository it reports:

- **Branch** — current branch (or `No Commits` for empty repos)
- **Status** — local state and remote sync combined, for example:
  - `Clean | Synced`
  - `Dirty | Ahead (2)`
  - `Staged | Behind (1)`
  - `Clean | No Remote`
  - `Clean | Local Only`
  - `Clean | Diverged (1A/2B)`

Directories listed in `exclude_dirs` (from `.chegi.json`) are skipped during traversal. Scanning does not enter subdirectories inside a discovered repository.

## Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `PATH` | Base directory to scan | `.` (current directory) |

## Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--max-depth` | `-d` | Override maximum directory traversal depth | from `.chegi.json` |
| `--workers` | `-w` | Number of concurrent worker threads | `5` |
| `--security` | `-s` | Run a security check on staged files in each repo | `false` |
| `--dirty` | | Only show repositories with uncommitted changes | `false` |
| `--staged` | | Only show repositories with staged files | `false` |

## Examples

Scan the current directory:

```bash
chegi scan
```

Scan a projects folder with a custom depth:

```bash
chegi scan ~/projects --max-depth 5
```

Show only dirty repositories with a security check:

```bash
chegi scan ~/work --dirty --security
```

Use more workers for large workspaces:

```bash
chegi scan ~/code --workers 10
```

## Output

Results are displayed in a Rich table with columns:

| Column | Description |
|--------|-------------|
| Repository | Full path to the repository |
| Branch | Current branch name |
| Status | Local state and remote sync status |

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Scan completed successfully |
| `1` | Invalid or missing directory |

## See Also

- [config](config.md) — configure `max_depth` and `exclude_dirs`
- [guard](guard.md) — security check for the current repository only
- [Security Policy](https://github.com/Ad-alwer/cheGi/blob/main/SECURITY.md) — security policy and sensitive file patterns
