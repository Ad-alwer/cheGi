# `chegi branch`

Manage Git branches — create, list, switch, merge, rename, delete, sync, and inspect branches with interactive prompts and direct subcommands.

## Synopsis

```bash
chegi branch [list|create|switch|merge|rename|delete|push-delete|sync|info] [ARGS]
```

## Description

`chegi branch` is a full branch manager. Run without arguments to open an interactive questionary menu. Each subcommand also works directly with arguments for power users.

### Interactive Menu

```bash
chegi branch
```

Opens a menu with all available operations:

```
🐆 cheGi Branch Manager
🌱 Current: main

? What would you like to do?
  ❯ List branches
    Create
    Switch
    Merge
    Rename
    Delete
    Push & Delete
    Sync
    Info
    Cancel
```

## Subcommands

### `list`

List all local branches with metadata (last commit message, author, upstream).

```bash
chegi branch list
chegi branch list --remote   # Show remote-tracking branches
```

### `create`

Create a new branch. Without a branch name, opens interactive prompts.

```bash
chegi branch create feature/new-thing
chegi branch create               # Interactive: asks for name, base, switch, push
```

In interactive mode you'll be asked:
1. Branch name
2. Base branch (current or another)
3. Whether to switch to it
4. Whether to push to origin

### `switch`

Switch to an existing branch. Without a name, shows a selectable list of branches.

```bash
chegi branch switch develop
chegi branch switch               # Interactive: pick from list
```

### `merge`

Merge a source branch into the current (or specified) target branch. Shows a commit preview before merging.

```bash
chegi branch merge feature/login
chegi branch merge feature/login main
```

The preview shows commits that will be merged. After merge, you'll be offered to push and/or delete the source branch.

### `rename`

Rename a branch.

```bash
chegi branch rename old-name new-name
chegi branch rename               # Interactive: pick branch + enter new name
```

### `delete`

Delete a branch. Protected branches (`main`, `master`, `develop`) cannot be deleted.

```bash
chegi branch delete feature/old
chegi branch delete feature/old --force   # Force delete even if unmerged
chegi branch delete                      # Interactive: pick from non-protected branches
```

### `push-delete`

Push a branch to origin, then delete it locally — the cleanup workflow for merged feature branches.

```bash
chegi branch push-delete feature/done
```

### `sync`

Prune remote-tracking branches that no longer exist on the remote.

```bash
chegi branch sync
chegi branch sync upstream   # Specify a different remote
```

### `info`

Show detailed information about a branch: upstream, ahead/behind counts, last commit details.

```bash
chegi branch info
chegi branch info feature/login
```

## Protected Branches

These branches cannot be deleted through `chegi branch delete`:

- `main`
- `master`
- `develop`

Trying to delete them raises a `ProtectedBranchError`.

## Exit Codes

| Code | Meaning |
|------|---------|
| `0`  | Success |
| `1`  | Error (branch not found, protected branch, merge conflict, etc.) |
