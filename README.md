# cheGi

**The ultimate Git companion. Type less, do more.**

[![PyPI version](https://img.shields.io/pypi/v/chegi)](https://pypi.org/project/chegi/)
[![PyPI downloads](https://img.shields.io/pypi/dm/chegi)](https://pypi.org/project/chegi/)
[![Python](https://img.shields.io/pypi/pyversions/chegi)](https://pypi.org/project/chegi/)
[![Tests](https://github.com/Ad-alwer/cheGi/actions/workflows/ci.yml/badge.svg)](https://github.com/Ad-alwer/cheGi/actions/workflows/ci.yml)
[![Documentation](https://img.shields.io/badge/docs-ad--alwer.github.io%2FcheGi-blue)](https://ad-alwer.github.io/cheGi/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Copr build status](https://copr.fedorainfracloud.org/coprs/alwer/cheGi/package/python-chegi/status_image/last_build.png)](https://copr.fedorainfracloud.org/coprs/alwer/cheGi/package/python-chegi/)
[![Docker pulls](https://img.shields.io/docker/pulls/adalwer/chegi)](https://hub.docker.com/r/adalwer/chegi)
[![Docker image](https://img.shields.io/docker/v/adalwer/chegi)](https://hub.docker.com/r/adalwer/chegi)

cheGi is a fast, developer-friendly CLI for managing Git across your entire workspace. Scan multiple repositories at once, catch secrets before they ship, sync branches safely, and automate the repetitive parts of your daily Git workflow — all from a single tool with a beautiful terminal UI.

cheGi donates **20% of all funding** to charity — local aid, disaster relief, and community causes. See [CHARITY.md](CHARITY.md) for details.

## Features

- **Workspace scan** — Discover Git repos concurrently and get a unified status overview
- **Branch manager** — List, create, switch, merge, rename, delete, sync branches
- **Smart clone** — Clone repos with user/repo shorthand, submodule init, smart .gitignore
- **Secure commit** — Guided commit with security checks and multiple commit styles
- **Security guard** — Detect sensitive files (`.env`, keys, tokens) in staged changes
- **Strict guard** — Scan both staged and unstaged files
- **History scan** — Scan all Git history across branches for leaked secrets
- **Git hooks** — Install pre-commit/pre-push hooks with automatic guard scanning
- **Safe sync** — Pull with rebase, push, and auto-stash when your tree is dirty
- **Commit reword** — Update commit messages interactively, including older commits
- **Project scaffolding** — Create new Git projects with .gitignore, license, README
- **Health check** — Comprehensive project health check with actionable suggestions
- **Environment setup** — Bootstrap dev toolchains (Python, Go, Rust, and more)
- **Gitignore generator** — Build `.gitignore` files from technology presets
- **Shell completions** — Generate completions for bash, zsh, fish, powershell
- **GitHub integration** — Browse repos, clone your own repos, push new projects
- **Token auth** — Encrypted token storage for GitHub and GitLab
- **Self-upgrade** — Auto-check for updates and upgrade from the CLI
- **Flexible config** — Per-workspace settings via `.chegi.json` or `.chegi/` directory
- **First-run wizard** — Guided setup on first use (Git identity, SSH keys, theme, auth)

## Requirements

- Python 3.8+
- [Git](https://git-scm.com/) installed and available on your `PATH`

## Installation

### All methods

| Method | Command |
|--------|---------|
| **pip** (PyPI) | `pip install chegi` |
| **Homebrew** (macOS) | `brew tap Ad-alwer/chegi && brew install chegi` |
| **Docker** | `docker pull adalwer/chegi` |
| **PPA** (Ubuntu/Debian) | `sudo add-apt-repository ppa:ad-alwer/chegi && sudo apt update && sudo apt install chegi` |
| **COPR** (Fedora) | `sudo dnf copr enable alwer/cheGi && sudo dnf install python3-chegi` |
| **AUR** (Arch Linux) | `yay -S chegi` *(pending submission)* |
| **WinGet** (Windows) | `winget install chegi` |
| **Binary** (Linux) | Download `.tar.gz`, `.deb`, or `.rpm` from [Releases](https://github.com/Ad-alwer/cheGi/releases) |
| **Binary** (macOS) | Download `.tar.gz` (universal2 — Intel + Apple Silicon) from [Releases](https://github.com/Ad-alwer/cheGi/releases) |
| **Binary** (Windows) | Download `.zip` or `.msi` from [Releases](https://github.com/Ad-alwer/cheGi/releases) |
| **Source** | `pip install git+https://github.com/Ad-alwer/cheGi.git` |

Platform support: Linux (amd64, arm64), macOS (Intel + Apple Silicon), Windows (amd64).

### From source (development)

```bash
git clone https://github.com/Ad-alwer/cheGi.git
cd cheGi
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Quick Start

```bash
# Scan all repositories under your projects folder
chegi scan ~/projects

# Check staged files for secrets before committing
chegi guard

# Interactive branch manager
chegi branch

# Clone a repo with smart defaults
chegi clone user/repo

# Scaffold a new project
chegi new my-app -t python

# Project health check
chegi doctor

# Safe sync
chegi sync

# Self-upgrade
chegi upgrade --check
```

## Commands

| Command | Description |
|---------|-------------|
| [`auth`](docs/commands/auth.md) | Manage token-based authentication for GitHub and GitLab |
| [`branch`](docs/commands/branch.md) | Full branch manager — list, create, switch, merge, rename, delete, sync, info |
| [`clone`](docs/commands/clone.md) | Clone repositories with smart defaults |
| [`co` / `br` / `ci` / `st`](docs/commands/aliases.md) | Git alias pass-through commands |
| [`commit`](docs/commands/commit.md) | Secure replacement for `git commit` with guided style selection |
| [`completions`](docs/commands/completions.md) | Generate shell completion scripts |
| [`config`](docs/commands/config.md) | Manage workspace settings, mirrors, and sensitive patterns |
| [`config git`](docs/commands/git-config.md) | View and modify Git global configuration |
| [`doctor`](docs/commands/doctor.md) | Comprehensive project health check |
| [`guard`](docs/commands/guard.md) | Check files for sensitive data before committing |
| [`hooks`](docs/commands/hooks.md) | Install Git hooks with automatic guard scanning |
| [`info`](docs/commands/info.md) | Quick project status dashboard |
| [`init`](docs/commands/init.md) | Initialize `.chegi/` project configuration directory |
| [`new`](docs/commands/new.md) | Scaffold new Git projects from scratch |
| [`repo`](docs/commands/repo.md) | List and browse GitHub repositories |
| [`reword`](docs/commands/reword.md) | Reword a commit message interactively |
| [`scan`](docs/commands/scan.md) | Scan a directory tree for Git repositories |
| [`setup`](docs/commands/setup.md) | Install and configure a development environment |
| [`sync`](docs/commands/sync.md) | Safely sync the current branch with its remote |
| [`upgrade`](docs/commands/upgrade.md) | Check for and install the latest version of cheGi |

Full documentation: **[ad-alwer.github.io/cheGi](https://ad-alwer.github.io/cheGi/)**

Run `chegi --help` or `chegi <command> --help` for built-in usage details.

## Configuration

Settings are stored in `.chegi.json` or `.chegi/config.json` at the root of your project:

```bash
chegi config list
chegi config set max_depth 5
chegi config exclude-add node_modules
```

- [Configuration Guide](docs/configuration.md) — full reference and troubleshooting
- [Security Guide](docs/security.md) — guard, hooks, and CI integration

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and [SECURITY.md](SECURITY.md) for the security policy.

## Development

```bash
pip install -e ".[dev]"
pytest -v
ruff check src tests
ruff format --check src tests
mkdocs build --strict
```

## License

MIT — see [LICENSE](LICENSE).
