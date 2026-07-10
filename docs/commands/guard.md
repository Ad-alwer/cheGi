# chegi guard

Check staged files for sensitive data before committing.

## Synopsis

```bash
chegi guard [OPTIONS]
```

## Description

`chegi guard` scans files currently in the Git staging area and matches their filenames against known sensitive patterns. If sensitive files are found, cheGi warns you and can automatically unstage them.

This command must be run inside a Git repository.

### Sensitive File Patterns

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

## Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--fix` | `-f` | Automatically unstage sensitive files without prompting | `false` |

## Examples

Interactive check (prompts to unstage if issues are found):

```bash
chegi guard
```

Non-interactive — auto-unstage for CI or pre-commit hooks:

```bash
chegi guard --fix
```

## Behavior

1. Verifies you are inside a Git repository
2. Lists all staged files (`git diff --cached --name-only`)
3. Matches filenames against sensitive patterns
4. If sensitive files are found:
   - Prints a warning with the file list
   - Shows the manual fix command: `git rm --cached <files>`
   - With `--fix`: unstages automatically
   - Without `--fix`: asks whether to unstage interactively
5. Exits with code `1` if sensitive files were found (useful for hooks)

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | No sensitive files found, or no staged files to check |
| `1` | Not a Git repository, or sensitive files detected |

## Pre-commit Hook

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

## See Also

- [scan](scan.md) — workspace scan with `--security`
- [Security Policy](https://github.com/Ad-alwer/cheGi/blob/main/SECURITY.md) — full security policy
