# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `chegi auth` token-based authentication system for GitHub and GitLab:
  - `AuthService` with encrypted token storage (Fernet via `cryptography`)
  - `login()` validates token via provider API before persisting
  - `logout()` / `status()` / `switch()` for credential management
  - `get_credential_for_host()` for Git credential helper protocol
  - Magic provider detection from token prefix (`ghp_` → GitHub, `glpat-` → GitLab)
  - Multiple account support with label-based switching per host
  - `Credential` model with `AuthProvider` enum (GitHub, GitLab)
  - 25 service-layer tests
- New dependency: `cryptography>=41.0.0` for secure token storage
- `chegi auth` CLI commands with non-interactive flag support:
  - `chegi auth login` — interactive and non-interactive (`--token`) modes
  - `chegi auth logout` — remove stored credentials (with `--all`)
  - `chegi auth status` — display saved accounts with host info
  - `chegi auth switch` — change the default account for a host
  - `chegi auth get-credential` — hidden Git credential helper command
  - Magic provider detection: auto-detects GitHub/GitLab from token prefix
  - 11 CLI integration tests using `CliRunner`
- Git credential helper integration:
  - `_setup_git_credential_helper()` — runs `git config --global` per host
  - `_remove_git_credential_helper()` — cleans up on `logout`
  - Non-interactive login auto-configures the helper; interactive asks confirmation
  - `get_credential_by_label()` service method for logout cleanup
  - 4 new CLI tests for helper setup/teardown
- Deep scope validation on login:
  - `validate_token()` now extracts scopes from GitHub `X-OAuth-Scopes` header
  - `check_required_scopes()` compares against recommended scopes per provider
  - Missing scope warnings shown during login and in `status` output
  - `login()` accepts pre-validated `username_from_api` + `scopes` to avoid double API call
  - 6 new scope-related service tests + 3 CLI tests
- Color theme system with support for switching between preset themes:
  - `TerminalUI` now loads themes dynamically from `GlobalConfig` with caching
  - `apply_theme()`, `get_active_theme()`, `_get_style()` methods on `TerminalUI`
  - `display_results_table()` uses active cheGi theme's `TableTheme` by default
  - Theme stored in `~/.config/chegi/config.json`, persisted across sessions
- First-run wizard now includes a theme picker step after project config:
  - Lists all available themes, marks the current one
  - Changes are applied immediately and persisted to global config
  - Logs `theme_changed` event with the chosen theme name
- `GlobalConfig` class for global user-level configuration (`~/.config/chegi/config.json`)
  - Exported from `chegi.config` public API
  - `theme` field with default value `"default"`
- 3 new tests for theme picker wizard step
- 7 new tests for themed TerminalUI
- First-run wizard now includes an SSH key check step:
  - Detects existing SSH key pairs (`id_ed25519`, `id_rsa`, etc.) in `~/.ssh/`
  - Checks if keys are loaded in `ssh-agent`
  - Offers to generate a new Ed25519 key pair with email label
  - Displays the public key with links to GitHub/GitLab settings
  - Offers to add the key to `ssh-agent` automatically
- `SSH_KEY_TYPES` constant for recognized SSH key filename patterns
- `_find_ssh_keys`, `_ssh_agent_has_keys`, `_generate_ssh_key`, `_add_key_to_agent`, `_display_public_key` helper methods
- 16 new tests covering all SSH key check scenarios
- Custom sensitive file pattern support:
  - `sensitive_patterns` field in `ChegiConfigModel`, persisted in `.chegi.json`/`.chegi/config.json`
  - `add_sensitive_pattern()` / `remove_sensitive_pattern()` / `get_all_sensitive_patterns()` in `ChegiConfig`
  - `SecurityGuard.find_sensitive_files()` accepts `extra_patterns` parameter for project-specific patterns
  - `SecurityGuard.scan_repo()`, `scan_strict()`, `scan_directory()` forward `extra_patterns`
  - CLI commands (`guard`, `commit`, `doctor`, `scan`) read custom patterns from config automatically
  - Wizard step `_step_sensitive_patterns()` asks users to add custom patterns during project setup
- 7 new config tests, 5 new security guard tests, 3 new wizard tests
- SSH key wizard step improvements:
  - Passphrase support — user can optionally protect the key with a passphrase
  - Backup existing key before overwriting (`id_ed25519.backup` + `.pub.backup`)
  - Auto-add entry to `~/.ssh/config` for GitHub with `IdentityFile` + `IdentitiesOnly`
  - Backup `~/.ssh/config` before modification (`config.chegi.backup`)
  - Event logging to `~/.config/chegi/wizard.log` with ISO timestamps
  - Restore instructions displayed after changes
- `_backup_key()`, `_backup_ssh_config()`, `_add_ssh_config_entry()`, `_log_wizard_event()` helper methods
- 12 new tests covering backup, config entry, and logging
- Wizard now checks and offers to install/upgrade GitHub CLI (`gh`):
  - Detects installed version and checks latest release via GitHub API
  - Offers to install if missing, upgrade if outdated
  - Automatically skipped when Git is not available
  - Logs `gh_installed` / `gh_upgraded` events
- Git check step now offers to install Git instead of exiting:
  - Shows installed version, prompts to install if missing
  - Sets `_git_available` flag to skip downstream steps when Git missing
  - Logs `git_installed` event
- `_get_git_version()` — returns parsed Git version string
- `_parse_gh_version()` — extracts version number from `gh --version` output
- `_check_latest_gh_version()` — fetches latest GitHub CLI release via API
- 15 new tests covering Git install flow, gh upgrade flow, and version helpers

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
