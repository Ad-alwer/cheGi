# chegi guard

Check staged files or Git history for sensitive data.

## Synopsis

```bash
chegi guard [OPTIONS]
chegi guard history [OPTIONS]
```

## Description

`chegi guard` scans files for sensitive data. It operates in two modes:

### Staged files scan (default)

Scans files currently in the Git staging area and matches their filenames against known sensitive patterns. If sensitive files are found, cheGi warns you and can automatically unstage them.

### History scan (`guard history`)

Scans all commits across all branches for sensitive files that were committed in the past. This helps detect secrets that were accidentally committed and are now part of the Git history.

## Options

### `chegi guard` (staged files)

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--fix` | `-f` | Automatically unstage sensitive files without prompting | `false` |

### `chegi guard history` (history scan)

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--report` | `-r` | Generate an HTML report of findings | `false` |
| `--fix` | `-f` | Remove detected files from Git history (requires confirmation) | `false` |

## Examples

### Staged files

Interactive check (prompts to unstage if issues are found):

```bash
chegi guard
```

Non-interactive — auto-unstage for CI or pre-commit hooks:

```bash
chegi guard --fix
```

### History scan

Scan entire Git history for secrets:

```bash
chegi guard history
```

Scan history and generate an HTML report:

```bash
chegi guard history --report
```

Scan history and remove detected files from all commits:

```bash
chegi guard history --fix
```

> **Danger:** `--fix` runs `git filter-branch` which rewrites Git history.
> cheGi will show you the exact commands to be executed and require explicit
> confirmation before proceeding.

## Sensitive File Patterns

| Pattern | Examples |
|---------|----------|
| `.env*` | `.env`, `.env.local`, `.env.production` |
| `*.pem` | `cert.pem` |
| `*.key` | `private.key` |
| `id_rsa*` | `id_rsa`, `id_rsa.pub` |
| `id_ecdsa*` | `id_ecdsa`, `id_ecdsa.pub` |
| `id_ed25519*` | `id_ed25519`, `id_ed25519.pub` |
| `*.pk8` | `key.pk8` |
| `*secret*` | `my_secret.json` |
| `credentials.json` | exact filename match |
| `*.jwt` | `token.jwt` |
| `*.token` | `session.token` |
| `.npmrc` | exact filename match |
| `.dockercfg` | exact filename match |
| `docker.json` | exact filename match |
| `service-account*.json` | `service-account-123.json` |
| `aws-credentials.json` | exact filename match |
| `*.credential` | `api.credential` |
| `*.cred` | `db.cred` |
| `*.passwd` | `shadow.passwd` |

> **Note:** Guard uses filename pattern matching only. It does not scan file contents.

Custom patterns can be added via `.chegi/guard-rules.json` (created by `chegi init`).

## HTML Report

When `--report` is used with `guard history`, an HTML report is generated in the current directory:

```
chegi-history-report.html
```

The report includes:
- Total commits scanned
- Number of secrets found
- Per-finding details: commit hash, file path, pattern matched, author, date, commit message
- Dark theme matching cheGi branding

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | No sensitive files found, or no staged files to check |
| `1` | Not a Git repository, or sensitive files detected |

## See Also

- [scan](scan.md) — workspace scan with `--security`
- [init](init.md) — create `.chegi/` directory with custom guard rules
- [Security Policy](https://github.com/Ad-alwer/cheGi/blob/main/SECURITY.md) — full security policy
