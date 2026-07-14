# chegi hooks

Manage Git hooks with automatic guard scanning.

## Synopsis

```bash
chegi hooks install [OPTIONS]
chegi hooks remove [OPTIONS]
chegi hooks status [OPTIONS]
```

## Description

`chegi hooks` installs Git hooks that automatically run `chegi guard` before commits or pushes.

Two hook types are supported:

- **Pre-commit** (default) — runs `chegi guard --fix` before every `git commit`. Sensitive files are auto-unstaged and the commit is aborted.
- **Pre-push** (`--pre-push`) — runs `chegi guard --fix` on staged files and `chegi guard --scan .` on unpushed commits before every `git push`. The push is aborted if sensitive data is found.

This prevents accidental commits or pushes of passwords, keys, `.env` files, and other sensitive data even when you forget to run `chegi guard` manually.

### `install`

Installs a Git hook that runs `chegi guard` at the appropriate stage.

- Creates `.git/hooks/pre-commit` or `.git/hooks/pre-push` with the guard script
- The hook is made executable
- If a hook already exists, the command fails unless `--force` is used
- Only hooks containing the cheGi marker are considered "cheGi hooks"

### `remove`

Removes the cheGi Git hook.

- Only removes hooks previously installed by `chegi hooks install`
- Custom hooks (not installed by cheGi) are left untouched
- Safe to run even when no hook is installed (exits with a message)

### `status`

Reports whether the cheGi hook is installed and shows the file path.

## Options

### `install`

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--path` | `-p` | Path to the Git repository | `.` |
| `--force` | `-f` | Overwrite existing hook | `False` |
| `--pre-push` | | Install a pre-push hook instead of pre-commit | `False` |

### `remove`

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--path` | `-p` | Path to the Git repository | `.` |
| `--pre-push` | | Remove a pre-push hook instead of pre-commit | `False` |

### `status`

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--path` | `-p` | Path to the Git repository | `.` |
| `--pre-push` | | Check pre-push hook status instead of pre-commit | `False` |

## Examples

Install the pre-commit guard hook:

```bash
chegi hooks install
```

Install the pre-push guard hook:

```bash
chegi hooks install --pre-push
```

Install in a specific project with force:

```bash
chegi hooks install -p ~/projects/my-app --force
```

Check status of pre-push hook:

```bash
chegi hooks status --pre-push
```

Remove the pre-push hook:

```bash
chegi hooks remove --pre-push
```

## See Also

- [guard](guard.md) — scan staged files for sensitive data
- [doctor](doctor.md) — full project health check
