# Security Guide

cheGi helps prevent accidental commits of sensitive files through its **Security Guard**. This guide covers how to use it in daily development, CI pipelines, and workspace scans.

> For vulnerability reporting and supported versions, see the [Security Policy](https://github.com/Ad-alwer/cheGi/blob/main/SECURITY.md).

## Overview

| Feature | Command | Scope |
|---------|---------|-------|
| Pre-commit check | `chegi guard` | Current repository, staged files |
| Strict check | `chegi guard --strict` | Staged + unstaged files |
| Directory scan | `chegi guard --scan <path>` | Any directory (no Git needed) |
| History scan | `chegi guard history` | All commits across all branches |
| History report | `chegi guard history --report` | HTML report of history findings |
| History fix | `chegi guard history --fix` | Remove detected files from history |
| Workspace audit | `chegi scan --security` | All repos in a scan path |
| Git hooks | `chegi hooks install` | Auto-guard on commit/push |
| Gitignore templates | `chegi gitignore` | Prevents tracking sensitive paths |
| Custom patterns | `sensitive_patterns` in `.chegi.json` | Project-specific filename patterns |

cheGi uses **filename pattern matching** — it checks whether file names match known sensitive patterns. It does **not** scan file contents.

Treat Security Guard as a safety net. For high-risk environments, combine it with dedicated secret-scanning tools (e.g. `gitleaks`, `trufflehog`).

---

## Sensitive File Patterns

These patterns are checked against the **filename** (not the full path):

| Pattern | Matches |
|---------|---------|
| `.env*` | `.env`, `.env.local`, `.env.production` |
| `*.pem` | `cert.pem`, `server.pem` |
| `*.key` | `private.key`, `api.key` |
| `id_rsa*` | `id_rsa`, `id_rsa.pub` |
| `id_ecdsa*` | `id_ecdsa`, `id_ecdsa.pub` |
| `id_ed25519*` | `id_ed25519`, `id_ed25519.pub` |
| `*.pk8` | `service-account.pk8` |
| `*secret*` | `my_secret.json`, `client_secret.txt` |
| `credentials.json` | exact filename |
| `*.jwt` | `token.jwt` |
| `*.token` | `session.token` |
| `.npmrc` | exact filename |
| `.dockercfg` | exact filename |
| `docker.json` | exact filename |
| `service-account*.json` | `service-account-123.json` |
| `aws-credentials.json` | exact filename |
| `*.credential` | `api.credential` |
| `*.cred` | `db.cred` |
| `*.passwd` | `shadow.passwd` |

Patterns are case-insensitive.

You can add project-specific patterns via `sensitive_patterns` in `.chegi.json` or `.chegi/guard-rules.json`. See [Custom Patterns](#custom-patterns) below.

---

## chegi guard

Run inside a Git repository before committing:

```bash
git add .
chegi guard
```

### Interactive mode (default)

If sensitive files are found:

1. Lists each matching file
2. Shows the manual fix: `git rm --cached <files>`
3. Asks whether to unstage automatically

### Non-interactive mode

For scripts, CI, and pre-commit hooks:

```bash
chegi guard --fix
```

Automatically unstages sensitive files without prompting.

### Strict mode

Scan both staged and unstaged files:

```bash
chegi guard --strict
```

If sensitive unstaged files are found, they are listed and you're prompted to unstage them. Useful as a final check before pushing.

### Directory scan

Recursively scan a directory for sensitive files (no Git repository needed):

```bash
chegi guard --scan ~/downloads
chegi guard --scan .
```

Scans all files in the given path against the same sensitive patterns.

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | Safe — no sensitive files found |
| `1` | Sensitive files found, or not inside a Git repository |

Use exit code `1` to **block commits** in hooks and CI.

---

## chegi guard history

Scan the entire Git history across all branches for sensitive files that were committed in the past.

```bash
chegi guard history
```

This is useful for catching secrets that were committed before you started using cheGi.

### HTML report

Generate a detailed HTML report with commit-by-commit findings:

```bash
chegi guard history --report
```

The report opens the `guard-history-report.html` file with a dark theme, commit details, and per-finding breakdown.

### Remove files from history

Permanently remove detected files from Git history via `git filter-branch`:

```bash
chegi guard history --fix
```

Lists all affected files and the exact commands to run. Requires explicit confirmation before execution. After removal, force-push instructions are displayed.

---

## chegi scan --security

Audit every repository in a workspace:

```bash
chegi scan ~/projects --security
```

Combine with filters to focus on active repos:

```bash
chegi scan ~/work --security --staged
chegi scan . --security --dirty
```

For each repository, cheGi checks staged files against the same patterns used by `chegi guard`.

---

## Git hooks

Install Git hooks that automatically run `chegi guard` before commits or pushes:

```bash
chegi hooks install          # Install pre-commit hook
chegi hooks install --pre-push  # Install pre-push hook
chegi hooks status           # Check hook installation status
chegi hooks remove           # Remove cheGi hooks
```

The pre-commit hook runs before each commit and blocks the commit if sensitive files are found. No configuration files needed — it works out of the box after `chegi hooks install`.

---

## Custom Patterns

You can extend the built-in sensitive patterns with project-specific filename patterns.

### Via `.chegi.json`

Add a `sensitive_patterns` array to your `.chegi.json`:

```json
{
    "sensitive_patterns": [
        "*.tfstate",
        "*.backup",
        "kubeconfig*"
    ]
}
```

### Via the first-run wizard

The wizard prompts you to add custom patterns during `chegi init`. You can also manage them later:

```bash
chegi config set sensitive_patterns '["*.tfstate", "kubeconfig*"]'
```

Custom patterns are merged with built-in defaults at scan time. Files matching either built-in or custom patterns are flagged.

---

## Integration Examples

### Pre-commit hook (via chegi)

```bash
chegi hooks install
```

### Pre-commit hook (via pre-commit framework)

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: chegi-guard
        name: chegi security guard
        entry: chegi guard --fix
        language: system
        pass_filenames: false
        always_run: true
```

Install:

```bash
pip install pre-commit
pre-commit install
```

### Git alias

```bash
git config --global alias.safe-commit '!chegi guard && git commit'
```

### CI pipeline (GitHub Actions)

```yaml
- name: Security guard
  run: |
    pip install chegi
    chegi guard --fix
```

Fails the job if sensitive files remain staged after `--fix`.

---

## Recommended Workflow

A practical setup for teams:

```
1. chegi hooks install      → auto-guard on every commit
2. chegi guard --strict     → final check before pushing
3. chegi guard history      → periodic history audit
```

For monorepos or multi-repo folders:

```bash
chegi scan ~/projects --security --staged
```

Run this before end-of-day pushes or in a scheduled CI job.

---

## What Guard Does Not Do

| Limitation | Detail |
|------------|--------|
| **No content scanning** | A file named `config.txt` with an API key inside will not be detected |
| **Filename only** | Patterns match file names, not directory paths |
| **Not a full SAST tool** | No code analysis, dependency scanning, or malware detection |

---

## Combining with .gitignore

`chegi gitignore` includes a global section that ignores common sensitive paths:

```
.env
.env.local
.env.*.local
```

Generate a project `.gitignore` early:

```bash
chegi gitignore
```

Guard catches files that were explicitly staged despite `.gitignore` (e.g. `git add -f`).

---

## Reporting Security Issues in cheGi

If you find a vulnerability **in cheGi itself** (not in your code), do not open a public GitHub issue.

Email **alwer.dev@gmail.com** — see the [Security Policy](https://github.com/Ad-alwer/cheGi/blob/main/SECURITY.md) for the full policy.

---

## See Also

- [guard command reference](commands/guard.md)
- [hooks command reference](commands/hooks.md)
- [scan command reference](commands/scan.md)
- [gitignore command reference](commands/gitignore.md)
- [Security Policy](https://github.com/Ad-alwer/cheGi/blob/main/SECURITY.md)
