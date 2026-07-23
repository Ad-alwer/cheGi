# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-07-22

### Added

- `chegi upgrade` — self-upgrade with auto-check, 24h cooldown, and changelog diff display
- `chegi branch` — full branch manager with interactive menu and 9 subcommands (create, switch, merge, rename, delete, push-delete, sync, info, list)
- `chegi clone` — clone repos with user/repo shorthand, submodule init, smart .gitignore, and .chegi/ setup
- `chegi commit` — secure replacement for `git commit` with auto security scan and 5 commit styles (Free, Conventional, Scope, Body, Gitmoji)
- `chegi new` — scaffold projects from scratch with templates (python, node, go, rust, cpp, csharp, ruby) and GitHub push integration
- `chegi info` — project status dashboard with branch, changes, contributors, security, and JSON/short/watch modes
- `chegi doctor` — comprehensive health check covering Git, identity, security, hooks, and stats
- `chegi hooks` — manage pre-commit and pre-push Git hooks with guard scanning
- `chegi auth` — encrypted token-based auth for GitHub and GitLab with scope validation and credential helper integration
- `chegi repo` — browse GitHub repos with fuzzy search, language colors, star count, and local cache
- `chegi completions` — shell completion scripts for bash, zsh, fish, and powershell with auto-install
- `chegi init` — initialize `.chegi/` project directory with config and guard rules
- `chegi config git` — manage Git global config (user.identity, editor, pull.rebase, fetch.prune) with interactive wizard
- `chegi co/br/ci/st` — fast Git alias pass-through commands (checkout, branch, commit, status)
- First-run wizard for new users — Git check, identity setup, SSH key, GitHub CLI, auth login, theme picker, and sensitive patterns
- `GitConfigService` — centralized Git global config operations (get, set, unset, get_all, identity)
- `GitHubRepoService` — create and list GitHub repositories with interactive picker
- `SecurityGuard` strict mode — scan both staged and unstaged files
- `SecurityGuard` directory scan — recursive sensitive file detection without Git repo
- Custom sensitive file patterns via `.chegi.json` config
- Color theme system with theme switching and `GlobalConfig` persistence
- macOS universal2 binary builds (Intel + Apple Silicon)
- Linux ARM64 native binary builds
- Docker multi-arch images (amd64 + arm64) on Docker Hub and GHCR
- `--version` / `-v` global flag

### Changed

- `chegi new` .gitignore generation now runs as a separate step with commit confirmation, matching the `chegi gitignore` command flow

### Fixed

- Improve `chegi auth` help text to clarify token vs SSH usage
- Add SSH detection in `chegi auth login` to inform users about token purpose
- Fix `chegi completions` crash on Linux with `RuntimeError: Shell detection not implemented for 'posix'`
- Fix Rich markup tags (`[bold]`, `[dim]`) displayed as raw text in `typer.confirm()` prompts (#39)
- Replace pepy.tech downloads badge with shields.io (pepy.tech had 404 errors)
- Fix Python version badge to use static badge (shields.io/pyversion endpoint doesn't exist)
- Fix Docker build: use `python:3.12-slim` instead of `debian:stable-slim` for final stage
- Fix Docker build: use non-editable pip install to avoid source path references
- Add `.dockerignore` to exclude `.git`, `__pycache__`, build artifacts
- Replace bare `except Exception` with specific exception types across services
- Replace `subprocess.run` with `GitClient` in services layer
- Replace `ValueError` raises with custom exception types in services
- Add missing type hints to all functions and parameters
- Add missing module docstrings to 34 source files
- Add missing `__init__.py` files to test directories
- Fix `__init__.py` directories that should have been files

### Changed

- Ask user before generating .gitignore in `chegi clone` and `chegi new`
- Ask user about GitHub connection in `chegi new` wizard
- Fix .gitignore creation when user selects no technologies
- AGENTS.md: enforce strict type hints with AST-based pre-commit gate
- AGENTS.md: add custom exceptions rule — never raise ValueError/TypeError/RuntimeError in services
- CONTRIBUTING.md: add strict type hint requirements for contributors

## [0.3.1] - 2026-07-11

### Added

- Docker image published to Docker Hub (`adalwer/chegi`) with automated build workflow
- Homebrew formula in `Ad-alwer/homebrew-chegi` repo with auto-update workflow
- COPR and Docker badges in README
- Comprehensive installation table in README (pip, Homebrew, Docker, PPA, COPR, AUR, source)

## [0.3.0] - 2026-05-29

### Added

- PyPI publish workflow via GitHub Actions
- Cross-platform release builds (Linux, Windows, macOS) with PyInstaller
- Detailed local and remote Git status tracking in `chegi scan`
- Interactive `.gitignore` generator with optional auto-commit (`chegi gitignore`)
- Package-manager mirror configuration (`chegi config mirror-*`)

### Changed

- Refactored gitignore commit message into shared branding constants
- Improved config mirror updates through `update_setting`

### Fixed

- Config mirror commands now persist changes correctly

## [0.2.1] - Earlier

### Added

- Core CLI commands: `scan`, `guard`, `sync`, `reword`, `setup`, `config`
- Concurrent workspace scanning with Rich terminal UI
- Security guard for staged sensitive files
- Environment presets for Python, JavaScript, Go, Rust, C++, C#, Ruby, and apps
- Preflight checks for Git installation

[Unreleased]: https://github.com/Ad-alwer/cheGi/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/Ad-alwer/cheGi/compare/v0.3.1...v0.4.0
[0.3.1]: https://github.com/Ad-alwer/cheGi/releases/tag/v0.3.1
[0.3.0]: https://github.com/Ad-alwer/cheGi/releases/tag/v0.3.0
[0.2.1]: https://github.com/Ad-alwer/cheGi/releases/tag/v0.2.1
