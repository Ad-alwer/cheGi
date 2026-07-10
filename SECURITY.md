# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.3.x   | ✅        |
| < 0.3   | ❌        |

## Reporting a Vulnerability

If you discover a security vulnerability in cheGi, please **do not** open a public issue.

Instead, report it privately by emailing **alwer.dev@gmail.com** with:

- A description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if you have one)

We aim to acknowledge reports within **48 hours** and provide a status update within **7 days**.

## Built-in Security Features

cheGi includes a **Security Guard** to help prevent accidental commits of sensitive files.

### `chegi guard`

Scans staged files in the current repository against known sensitive patterns:

- `.env*`
- `*.pem`, `*.key`, `id_rsa*`, `*.pk8`
- `*secret*`
- `credentials.json`

```bash
chegi guard          # interactive — prompts to unstage sensitive files
chegi guard --fix    # automatically unstage without prompting
```

Exit code `1` when sensitive files are found — suitable for pre-commit hooks and CI.

### `chegi scan --security`

Runs a security check across all repositories in a workspace scan.

### Pre-commit Hook Example

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

## Scope

The security guard uses filename pattern matching. It does **not** scan file contents for secrets. Treat it as a safety net, not a replacement for dedicated secret-scanning tools in high-risk environments.
