# Security Guide

cheGi helps prevent accidental commits of sensitive files through its **Security Guard**. This guide covers how to use it in daily development, CI pipelines, and workspace scans.

> For vulnerability reporting and supported versions, see the [Security Policy](https://github.com/Ad-alwer/cheGi/blob/main/SECURITY.md).

## Overview

| Feature | Command | Scope |
|---------|---------|-------|
| Pre-commit check | `chegi guard` | Current repository, staged files |
| Workspace audit | `chegi scan --security` | All repos in a scan path |
| Gitignore templates | `chegi gitignore` | Prevents tracking sensitive paths |

cheGi uses **filename pattern matching** — it checks whether staged file names match known sensitive patterns. It does **not** scan file contents.

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

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | Safe — no sensitive staged files (or nothing staged) |
| `1` | Sensitive files found, or not inside a Git repository |

Use exit code `1` to **block commits** in hooks and CI.

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

## Integration Examples

### Pre-commit hook

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
1. chegi gitignore          → ignore .env, keys, build artifacts
2. git add .
3. chegi guard              → catch anything that slipped through
4. git commit
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
| **Staged files only** | Unstaged sensitive files in the working tree are not checked |
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
- [scan command reference](commands/scan.md)
- [gitignore command reference](commands/gitignore.md)
- [Security Policy](https://github.com/Ad-alwer/cheGi/blob/main/SECURITY.md)
