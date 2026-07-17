# cheGi Documentation

**The ultimate Git companion. Type less, do more.**

cheGi is a command-line tool for developers who work with multiple Git repositories. It gives you a fast workspace overview, safer commits, and shortcuts for everyday Git tasks.

## Command Reference

| Command | Description |
|---------|-------------|
| [auth](commands/auth.md) | Manage token-based authentication for GitHub and GitLab |
| [branch](commands/branch.md) | Full branch manager — list, create, switch, merge, rename, delete, sync, info |
| [clone](commands/clone.md) | Clone repositories with smart defaults (submodules, .gitignore, .chegi/) |
| [co / br / ci / st](commands/aliases.md) | Git alias pass-through commands for checkout, branch, commit, status |
| [commit](commands/commit.md) | Secure replacement for `git commit` with guided style selection |
| [completions](commands/completions.md) | Generate shell completion scripts (bash, zsh, fish, powershell) |
| [config](commands/config.md) | Manage workspace settings, mirrors, and sensitive patterns |
| [config git](commands/git-config.md) | View and modify Git global configuration |
| [doctor](commands/doctor.md) | Comprehensive project health check |
| [guard](commands/guard.md) | Check staged files for sensitive data before committing |
| [hooks](commands/hooks.md) | Install Git hooks (pre-commit, pre-push) with automatic guard scanning |
| [info](commands/info.md) | Quick project status dashboard with Rich terminal UI |
| [init](commands/init.md) | Initialize `.chegi/` project configuration directory |
| [new](commands/new.md) | Scaffold new Git projects from scratch |
| [repo](commands/repo.md) | List and browse GitHub repositories |
| [reword](commands/reword.md) | Reword a commit message interactively |
| [scan](commands/scan.md) | Scan a directory tree for Git repositories and report their status |
| [setup](commands/setup.md) | Install and configure a development environment |
| [sync](commands/sync.md) | Safely sync the current branch with its remote |
| [upgrade](commands/upgrade.md) | Check for and install the latest version of cheGi |

## Quick Examples

```bash
chegi scan ~/projects                # Scan workspace for Git repos
chegi guard                          # Check staged files for secrets
chegi commit                         # Guided secure commit
chegi branch                         # Interactive branch manager
chegi clone user/repo                # Clone with smart defaults
chegi new my-app -t python           # Scaffold a new project
chegi info                           # Project status dashboard
chegi doctor                         # Full health check
chegi hooks install                  # Install pre-commit guard
chegi upgrade --check                # Check for cheGi updates
chegi completions bash               # Generate bash completions
chegi sync                           # Safe pull-rebase-push
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

Workspace settings are stored in `.chegi.json` or `.chegi/config.json`.

- [Configuration Guide](configuration.md) — full reference, scenarios, and troubleshooting
- [config command](commands/config.md) — CLI subcommands

## Security

- [Security Guide](security.md) — using guard, scan, hooks, and CI
- [Security Policy](https://github.com/Ad-alwer/cheGi/blob/main/SECURITY.md) — vulnerability reporting

## More

- [Contributing](https://github.com/Ad-alwer/cheGi/blob/main/CONTRIBUTING.md)
- [Security Policy](https://github.com/Ad-alwer/cheGi/blob/main/SECURITY.md)
- [Changelog](https://github.com/Ad-alwer/cheGi/blob/main/CHANGELOG.md)
