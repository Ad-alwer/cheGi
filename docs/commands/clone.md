# `chegi clone`

Clone a repository with smart defaults — submodule init, `.gitignore` generation, and `.chegi/` setup.

## Synopsis

```bash
chegi clone [URL] [OPTIONS]
```

## Description

`chegi clone` enhances the standard `git clone` workflow by automatically:

- Detecting and initializing submodules
- Generating `.gitignore` based on project files if none exists
- Setting up the `.chegi/` configuration directory

## Options

| Option | Short | Description |
|--------|-------|-------------|
| `--path` | `-p` | Target directory |
| `--here` | | Clone into current directory |
| `--own` | | Browse and clone from your GitHub repos |
| `--branch` | `-b` | Clone a specific branch |
| `--depth` | | Shallow clone depth |
| `--no-submodules` | | Skip submodule initialization |
| `--no-gitignore` | | Skip `.gitignore` generation |
| `--no-chegi` | | Skip `.chegi/` setup |

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
```

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Invalid URL, clone failed, target exists |
