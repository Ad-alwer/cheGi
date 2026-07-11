# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]


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
