# `chegi auth` — Token-Based Authentication

Manage authentication tokens for Git hosting providers (GitHub, GitLab).  
Once configured, cheGi automatically authenticates Git operations — no more password prompts.

## Overview

`chegi auth` stores your personal access tokens in an encrypted file
(`~/.config/chegi/auth/auth.json`) using Fernet symmetric encryption. Tokens are
never written to Git config or exposed in process listings.

## Commands

### `chegi auth login`

Interactive guided flow to add a new credential:

```
chegi auth login
```

1. Detects the provider from the token prefix automatically
2. Validates the token against the provider's API
3. Stores the credential encrypted
4. Displays token scopes and warns if recommended scopes are missing
5. Checks Git identity (`user.name` / `user.email`) and prompts to configure if needed
6. Offers to register a Git credential helper for automatic authentication

Supports multiple accounts on the same host (labels: `personal`, `work`, ...).

**Flags:**

| Flag | Description |
|------|-------------|
| `--token` `-t` | Token string (non-interactive mode, useful in CI) |
| `--username` `-u` | Git username (required in non-interactive mode) |
| `--provider` `-p` | Provider: `github` or `gitlab` |
| `--gitlab-url` | Base URL for self-hosted GitLab instances |
| `--label` `-l` | Account label (default: `default`) |

### `chegi auth logout`

Remove a stored credential:

```
chegi auth logout --label work
```

**Flags:**

| Flag | Description |
|------|-------------|
| `--label` `-l` | Label of the account to remove |
| `--all` `-a` | Remove all stored credentials |

### `chegi auth status`

Show all stored credentials and their authentication status:

```
chegi auth status
```

Example output:

```
GitHub     🔑 ad-alwer@github.com        ✅ Active (default)
GitLab     🔑 ali@gitlab.example.com     ✅ Active
```

### `chegi auth switch`

Switch the default account for a provider (useful when you have multiple
accounts on the same host, e.g. personal + work GitHub):

```
chegi auth switch work
```

### `chegi auth get-credential` (hidden)

Internal credential helper for Git. Called automatically by Git when
authentication is needed. Implements the Git credential helper protocol:

- Reads `host=...` from stdin
- Outputs `username=...` and `password=...` to stdout
- Returns the default credential for the requested host

## Configuration

Tokens are stored encrypted in `~/.config/chegi/auth/auth.json`.  
The encryption key lives in `~/.config/chegi/auth/auth.key`.

Both files are managed automatically — no manual editing required.

## Supported Providers

| Provider | Token Prefix | Default API URL | Required Scopes |
|----------|-------------|-----------------|-----------------|
| GitHub    | `ghp_`, `gho_`, `github_pat_` | `https://api.github.com` | `repo`, `read:user`, `workflow` |
| GitLab    | `glpat-` | `https://gitlab.com` (or custom) | `api`, `read_user` |

### Self-Hosted GitLab

Use the `--gitlab-url` flag with `login`:

```
chegi auth login --provider gitlab --gitlab-url https://gitlab.mycompany.com
```

## Examples

**First-time setup:**

```bash
chegi auth login
# → Paste your token → validated → scopes checked → identity check
# → credential helper registered → ready to sync
```

The first-run wizard also includes auth setup as a step — run any cheGi command
to trigger it:

```bash
chegi --help  # triggers wizard → includes auth login step
```

**Add a second GitHub account:**

```bash
chegi auth login --label work
# → Paste work token → stored as "work"
```

**Push without credentials:**

```bash
chegi sync
# → Git authenticates automatically via the stored token
```

**Direct `git push` also works:**

```bash
git push
# → Git calls chegi's credential helper → transparent auth
```

## Integration with Sync

If `chegi sync` fails due to an authentication error, it automatically detects
the issue and suggests running `chegi auth login`:

```bash
$ chegi sync
Sync Failed:
fatal: Authentication failed for 'https://github.com/user/repo.git'

⚠ This looks like an authentication issue.
  Run chegi auth login to set up token-based authentication.
```

## See Also

- [Sync command](sync.md) — pull + push in one command
- [Configuration guide](../configuration.md) — global config and theme settings
