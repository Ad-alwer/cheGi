# chegi new

Create a new Git project from scratch with scaffolding.

## Synopsis

```bash
chegi new [PROJECT_NAME] [OPTIONS]
```

## Description

`chegi new` scaffolds a complete Git project in one command. It creates a new directory with Git initialized, a `.gitignore`, a `.chegi/` project directory, `README.md`, an optional `LICENSE`, and makes an initial commit.

Run without arguments for an interactive guided flow:

```bash
chegi new
```

The interactive flow (default):
1. Prompts for a project name
2. Select technologies for `.gitignore` generation (checkbox)
3. Select a license type
4. Shows a summary and asks for confirmation before creation

## Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--path` | `-p` | Parent directory to create the project in | `.` |
| `--template` | `-t` | Predefined project template (python, node, go, rust, ...) | — |
| `--license` | `-l` | License type (mit, apache, gpl3) | — |
| `--no-readme` | | Skip `README.md` generation | `false` |
| `--no-gitignore` | | Skip `.gitignore` generation | `false` |
| `--yes` | `-y` | Non-interactive mode — use defaults for all prompts | `false` |

## Arguments

| Argument | Description |
|----------|-------------|
| `PROJECT_NAME` | Name of the project (creates a new directory with this name) |

## Examples

Interactive — prompts for project name, technologies, and license:

```bash
chegi new
```

Create a Python project:

```bash
chegi new my-app -t python
```

Create with specific options (non-interactive):

```bash
chegi new my-app --license mit --no-readme -y
```

Create in a specific parent directory:

```bash
chegi new my-app -p ~/projects
```

## Generated Files

| File | Purpose |
|------|---------|
| `.git/` | Git repository (via `git init`) |
| `.gitignore` | Technology-specific ignore rules |
| `.chegi/` | Project configuration directory |
| `README.md` | Project readme with getting started guide |
| `LICENSE` | Optional license file (MIT, Apache 2.0, or GPL v3) |
| Initial commit | `chore(new): initial project scaffold via cheGi 🐆` |

## See Also

- [init](init.md) — initialize `.chegi/` in an existing project
- [guard](guard.md) — scan staged files for sensitive data
