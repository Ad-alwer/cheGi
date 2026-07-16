# `chegi clone`

Clone a repository with smart defaults — submodule init, `.gitignore` generation, and `.chegi/` setup.

## Synopsis

```bash
chegi clone [URL] [OPTIONS]
```

## Description

`chegi clone` enhances the standard `git clone` workflow by automatically:

- Expanding `user/repo` shorthand to `https://github.com/user/repo.git`
- Detecting and initializing submodules
- Generating `.gitignore` based on project files if none exists
- Setting up the `.chegi/` configuration directory

If no URL is provided, an interactive mode guides you through selecting a source
(one of your GitHub repos or an external URL) and the target location.

### Shorthand Expansion

A URL in the form `owner/repo` is automatically expanded to
`https://github.com/owner/repo.git`. Full URLs and SSH URLs are passed through
unchanged.

### Smart `.gitignore` Detection

After cloning, cheGi scans the target directory for well-known project files:

| File | Technology |
|------|-----------|
| `package.json` | Node.js |
| `Cargo.toml` | Rust |
| `go.mod` | Go |
| `pyproject.toml` | Python |
| `requirements.txt` | Python |
| `Gemfile` | Ruby |
| `build.gradle` | Gradle |
| `pom.xml` | Maven |

If a `.gitignore` does not already exist, one is generated using templates for
the detected technologies. In interactive mode, you can select or modify
the technologies via a checkbox prompt.

### Interactive `.gitignore` Selection

In interactive mode (no URL argument), cheGi prompts you to select
technologies for `.gitignore` generation from a checkbox list of all
available environments. In direct mode (URL provided), technologies are
auto-detected from the cloned project files.

### Submodule Detection

If the cloned repository contains a `.gitmodules` file, cheGi automatically
runs `git submodule update --init --recursive` to initialize submodules.
Use `--no-submodules` to skip this step.

### `.chegi/` Setup

If `--no-chegi` is not specified, cheGi initializes a `.chegi/` directory
with default guard rules, config, and `.chegiignore` file.

### Safety Check

If the target directory already exists and is not empty, cheGi warns you
and asks for confirmation before proceeding.

## Options

| Option | Short | Description |
|--------|-------|-------------|
| `--path` | `-p` | Target directory path |
| `--here` | | Clone into current directory (no subfolder) |
| `--own` | | Browse and clone from your GitHub repositories |
| `--branch` | `-b` | Clone a specific branch |
| `--depth` | | Shallow clone depth |
| `--no-submodules` | | Skip submodule initialization |
| `--no-gitignore` | | Skip `.gitignore` generation |
| `--no-chegi` | | Skip `.chegi/` directory setup |

## Examples

```bash
# Interactive mode
chegi clone

# Direct clone with shorthand
chegi clone user/repo

# Full URL with path
chegi clone https://github.com/user/repo.git --path ./my-folder

# Clone into current directory
chegi clone user/repo --here

# Shallow clone with specific branch
chegi clone user/repo --branch develop --depth 1

# Clone without extras
chegi clone user/repo --no-submodules --no-gitignore --no-chegi

# Browse and clone one of your GitHub repos
chegi clone --own
```

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Invalid URL, clone failed, target exists and not confirmed |
