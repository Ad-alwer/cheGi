# chegi sync

Safely sync the current Git repository with its remote.

## Synopsis

```bash
chegi sync
```

## Description

`chegi sync` performs a safe pull-and-push workflow for the repository in your current working directory:

1. Checks whether the workspace is clean
2. If dirty, stashes uncommitted changes
3. Pulls from remote with rebase (`git pull --rebase`)
4. Pushes local commits to remote
5. Restores the stash if one was created

The stash is restored even if pull or push fails, so your local changes are not lost.

## Requirements

- Must be run inside a Git repository
- Git must be installed and available on your `PATH`
- A configured remote and upstream branch are required for pull/push to succeed

## Examples

From inside any repository:

```bash
cd my-project
chegi sync
```

## Workflow

```
┌─────────────────┐
│ Workspace clean?│
└────────┬────────┘
         │ no → stash changes
         ▼
┌─────────────────┐
│  pull --rebase  │
└────────┬────────┘
         ▼
┌─────────────────┐
│      push       │
└────────┬────────┘
         │ had stash → pop stash
         ▼
       Done ✨
```

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Repository synced successfully |
| `1` | Git operation failed or unexpected error |

## Authentication Failures

If `chegi sync` fails with an authentication error (e.g., expired token, no
credentials configured), it detects the issue and suggests a fix:

```
Sync Failed:
fatal: Authentication failed for 'https://github.com/user/repo.git'

⚠ This looks like an authentication issue.
  Run chegi auth login to set up token-based authentication.
```

Run `chegi auth login` to set up token-based authentication with automatic
credential helper configuration. Once configured, `chegi sync` uses the stored
token transparently.

## See Also

- [scan](scan.md) — check remote sync status across multiple repos
- [auth](auth.md) — set up token-based authentication
