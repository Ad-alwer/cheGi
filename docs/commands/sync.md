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

## See Also

- [scan](scan.md) — check remote sync status across multiple repos
