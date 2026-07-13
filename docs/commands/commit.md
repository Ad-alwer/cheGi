# chegi commit

Record changes to the repository with built-in security checks and smart defaults.

## Synopsis

```bash
chegi commit [OPTIONS]
```

## Description

`chegi commit` is a secure replacement for `git commit`. It automatically:

1. **Scans staged files** for sensitive data (secrets, credentials, keys)
2. **Shows a styled diff summary** of staged changes
3. **Guides you step-by-step** with commit style selection, field filling, and preview
4. **Suggests commit messages** based on what was changed
5. **Executes the commit** after validation

## Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--message` | `-m` | The commit message (skips interactive prompt) | `null` |
| `--force` | | Commit even if sensitive files are detected | `false` |
| `--chegi-header` | `--ch` | Add the cheGi brand signature `🐆` to the subject line | `false` |

## Interactive Flow

When called without `-m`, `chegi commit` walks you through a guided flow:

1. **Security scan** — auto-runs guard on staged files
2. **Styled diff** — file names shown in brand color
3. **Style selection** — choose from 5 built-in styles:
   - **Free** — just a description, no prefix
   - **Conventional** — `type: description`
   - **Conventional with scope** — `type(scope): description`
   - **Conventional with body** — `type(scope): description + body bullets`
   - **Gitmoji** — `emoji type: description`
4. **Field filling** — prompts based on your style choice (type, scope, description, body)
5. **Preview** — shows the final message in a styled panel
6. **Confirmation** — asks before executing
7. **Brand hint** — on your first single-line commit, shows a tip about `--ch`

## Examples

### Interactive commit (recommended)

```bash
chegi commit
```

### With inline message

```bash
chegi commit -m "feat: add user authentication"
```

Skips the interactive prompt but still runs security checks.

### With brand signature

```bash
chegi commit -m "feat: add login" --ch
```

Appends `🐆` to the subject line: `feat: add login 🐆`

### Force commit with sensitive files

```bash
chegi commit --force
```

### Brand signature in guided mode

```bash
chegi commit --ch
```

## Commit Styles

### Free
```
init project
```

### Conventional
```
feat: init project
```

### Conventional with scope
```
feat(init): Init project
```

### Conventional with body
```
feat(init): Init project

- Set up project structure
- Add configuration files
```

### Gitmoji
```
✨ feat: init project
```

### Custom Styles

Create `.chegi/commit-styles.json` in your repository:

```json
{
  "styles": [
    {
      "name": "custom-prefix",
      "label": "Custom Prefix",
      "description": "prefix: description",
      "fields": ["prefix", "description"]
    }
  ]
}
```

## Security Flow

When sensitive files are detected in staging, cheGi presents three options:

1. **Unstage sensitive files and continue** — removes the files from staging and proceeds
2. **Force commit anyway** — commits with sensitive files (not recommended)
3. **Abort commit** — exits without committing

## Brand Signature

Use `--ch` or `--chegi-header` to add `🐆` at the end of the subject line:

```
feat(auth): add login functionality 🐆
```

This is a single-line addition — the body is never modified.

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Commit successful |
| `1` | Not a Git repository, no staged files, sensitive files detected, commit failed, or user aborted |

## See Also

- [guard](guard.md) — security scanning for sensitive files
- [init](init.md) — initialize cheGi project directory with custom guard rules
