# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `.chegi/` project directory infrastructure with `chegi init` command
  - `config.json` — per-project configuration overrides
  - `guard-rules.json` — custom sensitive file patterns
  - `.chegiignore` — scan exclusion patterns (.gitignore syntax)
  - Auto-adds `.chegi/` to `.gitignore`
- Config system now merges `.chegi/config.json` over `.chegi.json` with higher priority
- `InitService` for creating and loading cheGi projects
- `InitService.find_project_root()` walks up directories to locate `.chegi/`
- Full test coverage for init service (14 tests), CLI (5 tests), and config merging (2 tests)
- `chegi guard history` subcommand — scan Git history for secrets across all branches
- `chegi guard history --report` — generate HTML report of history scan findings
- `chegi guard history --fix` — remove detected files from Git history via `git filter-branch`
  - Shows red DESTRUCTIVE ACTION warnings before execution
  - Lists all affected files and exact commands to run
  - Requires explicit user confirmation (`--fix` alone is not enough)
  - Executes removal per-file and reports success/failure
  - Shows force-push instructions after completion
- `GuardHistoryService` for scanning Git history with filename-based pattern matching
- `GuardHistoryService.remove_file_from_history()` method for programmatic removal
- History scan respects `.chegi/guard-rules.json` custom patterns and `.chegiignore` excludes
- HTML report with dark theme, commit details, and per-finding breakdown
- 14 tests for history scanning service, 4 tests for CLI history subcommand

### Changed

- AGENTS.md: enforced changelog updates as pre-commit requirement with CRITICAL section
- `guard --history` / `--report` / `--auto-remove` flags replaced by `guard history` subcommand with `--report` and `--fix` flags

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

[Unreleased]: https://github.com/Ad-alwer/cheGi/compare/v0.3.1...HEAD
[0.3.1]: https://github.com/Ad-alwer/cheGi/releases/tag/v0.3.1
[0.3.0]: https://github.com/Ad-alwer/cheGi/releases/tag/v0.3.0
[0.2.1]: https://github.com/Ad-alwer/cheGi/releases/tag/v0.2.1
