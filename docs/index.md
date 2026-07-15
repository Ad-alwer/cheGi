# cheGi Documentation

**The ultimate Git companion. Type less, do more.**

cheGi is a command-line tool for developers who work with multiple Git repositories. It gives you a fast workspace overview, safer commits, and shortcuts for everyday Git tasks.

## Command Reference

| Command | Description |
|---------|-------------|
| [auth](commands/auth.md) | Manage token-based authentication for GitHub and GitLab |
| [scan](commands/scan.md) | Scan a directory tree for Git repositories and report their status |
| [guard](commands/guard.md) | Check staged files for sensitive data before committing |
| [sync](commands/sync.md) | Safely sync the current branch with its remote |
| [reword](commands/reword.md) | Reword a commit message interactively |
| [setup](commands/setup.md) | Install and configure a development environment |
| [gitignore](commands/gitignore.md) | Generate a `.gitignore` file from technology presets |
| [config](commands/config.md) | Manage workspace settings and package-manager mirrors |

## Quick Examples

```bash
chegi scan ~/projects
chegi scan . --dirty --security
chegi guard
chegi sync
chegi reword --last 10
chegi setup python -y
chegi gitignore --commit
chegi config list
```

## Global Options

These flags are available on every `chegi` command.

| Option | Short | Description |
|--------|-------|-------------|
| `--version` | `-v` | Show the cheGi version and exit |

**Example:**

```bash
chegi --version
chegi -v
```

## Configuration

Workspace settings are stored in `.chegi.json`.

- [Configuration Guide](configuration.md) — full reference, scenarios, and troubleshooting
- [config command](commands/config.md) — CLI subcommands

## Security

- [Security Guide](security.md) — using guard, scan, hooks, and CI
- [Security Policy](https://github.com/Ad-alwer/cheGi/blob/main/SECURITY.md) — vulnerability reporting

## More

- [Contributing](https://github.com/Ad-alwer/cheGi/blob/main/CONTRIBUTING.md)
- [Security Policy](https://github.com/Ad-alwer/cheGi/blob/main/SECURITY.md)
- [Changelog](https://github.com/Ad-alwer/cheGi/blob/main/CHANGELOG.md)
