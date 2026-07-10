# chegi gitignore

Generate a `.gitignore` file interactively from technology presets.

## Synopsis

```bash
chegi gitignore [OPTIONS]
```

## Description

`chegi gitignore` builds a `.gitignore` file by combining templates for the technologies you select. Templates are merged and deduplicated. A global section (macOS, Windows, IDEs, logs, `.env`) is always included.

If the target directory is a Git repository, cheGi can optionally stage and commit the generated file.

## Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--path` | `-p` | Directory to write `.gitignore` | `.` |
| `--commit` | `-c` | Automatically commit the generated file | prompted if in a repo |

### Available Technology Templates

| Template | Source preset |
|----------|---------------|
| Apps | `apps` |
| Cpp | `cpp` |
| Csharp | `csharp` |
| Go | `go` |
| Javascript | `javascript` |
| Python | `python` |
| Ruby | `ruby` |
| Rust | `rust` |

## Examples

Generate a `.gitignore` in the current directory:

```bash
chegi gitignore
```

Generate and auto-commit:

```bash
chegi gitignore --commit
```

Write to a specific project folder:

```bash
chegi gitignore --path ~/projects/my-app
```

## Behavior

1. Shows an interactive checkbox to select technologies
2. Warns before overwriting an existing `.gitignore`
3. Writes the merged file to the target path
4. If inside a Git repo:
   - `--commit` → commits immediately
   - no flag → asks whether to commit (default: yes)
5. Default commit message: `chore(gitignore): auto add .gitignore via cheGi 🐆`

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Cancelled, no templates found, overwrite declined, or error |

## See Also

- [setup](setup.md) — install dev tools for the technologies you select
- [guard](guard.md) — prevent committing sensitive files like `.env`
