# chegi hooks

Manage Git hooks with automatic guard scanning.

## Synopsis

```bash
chegi hooks install [OPTIONS]
chegi hooks remove [OPTIONS]
```

## Description

`chegi hooks` installs a pre-commit hook that automatically runs `chegi guard --fix` before every `git commit`. If sensitive files are detected in the staging area, they are unstaged and the commit is aborted with a clear message.

This prevents accidental commits of passwords, keys, `.env` files, and other sensitive data even when you forget to run `chegi guard` manually.

### `install`

Installs a pre-commit hook that runs `chegi guard --fix` before each commit.

- Creates `.git/hooks/pre-commit` with the guard script
- The hook is made executable
- If a pre-commit hook already exists, the command fails unless `--force` is used
- Only hooks containing the cheGi marker are considered "cheGi hooks"

### `remove`

Removes the cheGi pre-commit hook.

- Only removes hooks previously installed by `chegi hooks install`
- Custom pre-commit hooks (not installed by cheGi) are left untouched
- Safe to run even when no hook is installed (exits with a message)

## Options

### `install`

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--path` | `-p` | Path to the Git repository | `.` |
| `--force` | `-f` | Overwrite existing pre-commit hook | `False` |

### `remove`

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--path` | `-p` | Path to the Git repository | `.` |

## Examples

Install the guard hook:

```bash
chegi hooks install
```

Install in a specific project:

```bash
chegi hooks install -p ~/projects/my-app
```

Force overwrite an existing hook:

```bash
chegi hooks install --force
```

Remove the cheGi hook:

```bash
chegi hooks remove
```

## See Also

- [guard](guard.md) — scan staged files for sensitive data
- [doctor](doctor.md) — full project health check
