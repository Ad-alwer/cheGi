# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `chegi new` command — scaffold complete Git projects from scratch with:
  - Interactive questionary-first guided flow (project name, tech selection, license, summary confirmation)
  - Non-interactive mode with `--yes` / `-y` and `--template` / `-t` flags
  - Git init, `.gitignore` generation (per-technology), `.chegi/` directory, `README.md`, optional `LICENSE`
  - Automatic initial commit with brand message
  - Project templates via `--template` (python, node, go, rust, cpp, csharp, ruby)
  - License options: MIT, Apache 2.0, GNU GPL v3
- `NewProjectService` — core service for scaffolding projects with:
  - `NewProjectConfig` and `NewProjectResult` dataclasses
  - `ProjectAlreadyExistsError`, `GitInitError`, `ProjectCreationError` exceptions
  - License templates for MIT, Apache 2.0, and GPL v3
  - Template-to-tech mapping for `--template` flag
- Full test coverage: 19 service tests + 7 CLI tests
- Documentation at `docs/commands/new.md`
- `chegi doctor` command — comprehensive project health check with:
  - Health checks: Git installation, identity, .gitignore, .chegi/ config
  - Security checks: staged sensitive files, .env tracking, pre-commit hooks
  - Stats checks: commit count, branches, remote status
  - Color-coded Rich output: green (pass), yellow (warn), red (fail)
  - Actionable suggestions for each issue found
- `DoctorService` with `DoctorReport`, `CheckResult`, `CheckCategory`, `CheckStatus` models
  - History secrets scan via `GuardHistoryService`
  - Contributor count via `git shortlog`
  - Remote sync status (ahead/behind vs upstream)
- Full test coverage: 34 service tests + 5 CLI tests
- Documentation at `docs/commands/doctor.md`
- `chegi hooks` command — manage Git hooks with automatic guard scanning:
  - `chegi hooks install` — installs a guard hook (pre-commit by default, `--pre-push` for pre-push)
  - `chegi hooks remove` — removes the cheGi hook (non-cheGi hooks left untouched)
  - `chegi hooks status` — check installation status with file path
  - `--pre-push` flag for all subcommands to target pre-push hooks
  - `--force` / `-f` flag to overwrite existing hooks
  - `--path` / `-p` flag for targeting specific repositories
- `HooksService` with `HookType` enum, `HookInfo` model, `HookInstallError`, `HookRemoveError` exceptions
  - Generic `install(hook_type, force)`, `remove(hook_type)`, `is_installed(hook_type)` API
  - Marker-based identification via per-type cheGi markers
  - Pre-push hook template checks staged files AND unpushed commits
- Full test coverage: 22 service tests + 12 CLI tests
- Documentation at `docs/commands/hooks.md`

- `guard --strict` / `-S` — scan both staged and unstaged files with auto-unstage
- `guard --scan <path>` — recursive directory scan for sensitive files (no Git repo needed)
- `SecurityGuard.get_unstaged_files()`, `.scan_strict()`, `.scan_directory()` methods
- 16 new tests for guard strict/scan modes
- Documentation for `--strict` and `--scan` in `docs/commands/guard.md`
- `chegi commit` command — secure replacement for `git commit` with:
  - Auto `SecurityGuard` scan on staged files before each commit
  - Styled diff display with brand-colored file names
  - Questionary guided flow with 5 commit styles (Free, Conventional, Scope, Body, Gitmoji)
  - `--ch` / `--chegi-header` flag for brand signature (` 🐆`) on subject line
  - One-time brand hint on first single-line interactive commit
  - Extensible commit styles via `.chegi/commit-styles.json`
  - Last-used style persistence in `~/.config/chegi/prefs.json`
  - Interactive sensitive file handling (unstage/force/abort)
- `CommitService` — core service with `build_message()` (style→message builder) and `apply_brand_suffix()`
- `CommitStyle` dataclass for defining commit message formats
- `CommitStyleManager` — manages style preferences, hints, and custom styles
- `BRAND_SUFFIX` and `BUILTIN_STYLES` constants
- Documentation at `docs/commands/commit.md`
- 35+ tests for commit service and CLI
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
- `--version` / `-v` global flag to show cheGi version and exit
- `chegi guard history --fix` — remove detected files from Git history via `git filter-branch`
  - Lists all affected files and exact commands to run
  - Requires explicit user confirmation (`--fix` alone is not enough)
  - Executes removal per-file and reports success/failure
  - Shows force-push instructions after completion
- `GuardHistoryService` for scanning Git history with filename-based pattern matching
- `GuardHistoryService.remove_file_from_history()` method for programmatic removal
- History scan respects `.chegi/guard-rules.json` custom patterns and `.chegiignore` excludes
- HTML report with dark theme, commit details, and per-finding breakdown
- 14 tests for history scanning service, 4 tests for CLI history subcommand
- First-run wizard (`WizardService`) — auto-triggers on first `chegi` command
  - Shows welcome banner with ASCII art cheGi logo
  - Checks Git installation
  - Checks Git identity (`user.name`, `user.email`)
  - Interactive prompt to configure Git identity if not set
  - Offers to create `.chegi/` project directory via `InitService`
  - Writes `~/.config/chegi/wizard_done` marker to run only once
  - Skips automatically when not in a TTY (CI, piped commands)
- 11 tests for wizard service

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
