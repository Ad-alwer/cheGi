# cheGi

**The ultimate Git companion. Type less, do more.**

[![PyPI version](https://img.shields.io/pypi/v/chegi)](https://pypi.org/project/chegi/)
[![PyPI downloads](https://img.shields.io/pypi/dm/chegi)](https://pypi.org/project/chegi/)
[![Python](https://img.shields.io/pypi/pyversions/chegi)](https://pypi.org/project/chegi/)
[![Documentation](https://img.shields.io/badge/docs-ad--alwer.github.io%2FcheGi-blue)](https://ad-alwer.github.io/cheGi/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Copr build status](https://copr.fedorainfracloud.org/coprs/alwer/cheGi/package/python-chegi/status_image/last_build.png)](https://copr.fedorainfracloud.org/coprs/alwer/cheGi/package/python-chegi/)
[![Docker pulls](https://img.shields.io/docker/pulls/adalwer/chegi)](https://hub.docker.com/r/adalwer/chegi)
[![Docker image](https://img.shields.io/docker/v/adalwer/chegi)](https://hub.docker.com/r/adalwer/chegi)

cheGi is a fast, developer-friendly CLI for managing Git across your entire workspace. Scan multiple repositories at once, catch secrets before they ship, sync branches safely, and automate the repetitive parts of your daily Git workflow — all from a single tool with a beautiful terminal UI.

cheGi donates **20% of all funding** to charity — local aid, disaster relief, and community causes. See [CHARITY.md](CHARITY.md) for details.

## Features

- **Workspace scan** — Discover Git repos concurrently and get a unified status overview
- **Security guard** — Detect sensitive files (`.env`, keys, tokens) in staged changes
- **Safe sync** — Pull with rebase, push, and auto-stash when your tree is dirty
- **Commit reword** — Update commit messages interactively, including older commits
- **Environment setup** — Bootstrap dev toolchains (Python, Go, Rust, and more)
- **Gitignore generator** — Build `.gitignore` files from technology presets
- **Flexible config** — Per-workspace settings via `.chegi.json`

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
| **Source** | `pip install git+https://github.com/Ad-alwer/cheGi.git` |

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

# Sync the current repository (pull --rebase, then push)
chegi sync
```

## Commands

| Command | Description |
|---------|-------------|
| [`scan`](docs/commands/scan.md) | Scan a directory tree for Git repositories and report their status |
| [`guard`](docs/commands/guard.md) | Check staged files for sensitive data before committing |
| [`sync`](docs/commands/sync.md) | Safely sync the current branch with its remote |
| [`reword`](docs/commands/reword.md) | Reword a commit message interactively |
| [`setup`](docs/commands/setup.md) | Install and configure a development environment |
| [`gitignore`](docs/commands/gitignore.md) | Generate a `.gitignore` file from technology presets |
| [`config`](docs/commands/config.md) | Manage workspace settings and package-manager mirrors |

Full documentation: **[ad-alwer.github.io/cheGi](https://ad-alwer.github.io/cheGi/)**

Run `chegi --help` or `chegi <command> --help` for built-in usage details.

## Configuration

Settings are stored in `.chegi.json` at the root of your scan path:

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
```

## License

MIT — see [LICENSE](LICENSE).
