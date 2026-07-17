# Configuration Guide

cheGi stores workspace settings in a `.chegi.json` file or a `.chegi/` directory. This guide explains how configuration works, what each setting does, and how to customize it for your workflow.

## Overview

| Topic | Details |
|-------|---------|
| **File name** | `.chegi.json` or `.chegi/config.json` |
| **Format** | JSON |
| **Scope** | Per workspace directory |
| **Managed via** | `chegi init`, `chegi config` commands, or manual editing |

Configuration is loaded relative to the path you pass to commands. For example, `chegi scan ~/projects` loads `~/projects/.chegi.json` (and `~/projects/.chegi/config.json`) if they exist.

If no file is present, cheGi uses built-in defaults.

> **Note:** Starting with v0.4.0, cheGi supports a `.chegi/` directory managed via `chegi init`. Settings in `.chegi/config.json` take precedence over `.chegi.json`. The `.chegi/` directory can also contain `guard-rules.json` (custom sensitive patterns) and `.chegiignore` (scan exclusion patterns).

## File Location

```
~/projects/
├── .chegi.json       ← config for this workspace
├── app-a/
│   └── .git/
└── app-b/
    └── .git/
```

Create or update settings with the CLI:

```bash
cd ~/projects
chegi config list
chegi config set max_depth 5
```

Or edit `.chegi.json` directly — cheGi will read it on the next run.

## Default Configuration

When no `.chegi.json` exists, cheGi starts with these defaults:

```json
{
    "exclude_dirs": [
        "node_modules",
        ".venv",
        "venv",
        "env",
        ".tox",
        "__pycache__",
        ".idea",
        ".vscode",
        ".git"
    ],
    "max_depth": 3,
    "mcts": 10,
    "mirrors": {},
    "sensitive_patterns": []
}
```

## Configuration Reference

### `exclude_dirs`

| | |
|---|---|
| **Type** | `string[]` |
| **Used by** | `chegi scan` |
| **Default** | See above |

Directory **names** (not full paths) that `chegi scan` skips during traversal. This speeds up scans by avoiding heavy folders like `node_modules` and virtual environments.

**How merging works:** When you load a `.chegi.json`, values in `exclude_dirs` **replace** the built-in defaults — they do not merge with them. If you want to keep default excludes alongside custom ones, include them in the file.

```bash
chegi config exclude-add dist
chegi config exclude-remove .vscode
```

**Example — monorepo workspace (include defaults explicitly if you want them):**

```json
{
    "exclude_dirs": [
        "node_modules",
        ".venv",
        "target",
        "build",
        "dist"
    ]
}
```

Without explicit defaults in the file, only `target`, `build`, and `dist` would be excluded.

---

### `max_depth`

| | |
|---|---|
| **Type** | `integer` |
| **Used by** | `chegi scan` |
| **Default** | `3` |

Maximum depth of directory traversal **below the scan path**.

Depth is measured from the directory you pass to `chegi scan`:

```
~/projects/          ← depth 0 (scan root)
├── client/          ← depth 1
│   └── src/         ← depth 2
│       └── utils/   ← depth 3  (included when max_depth = 3)
│           └── x/   ← depth 4  (skipped when max_depth = 3)
```

Override per run without changing the config:

```bash
chegi scan . --max-depth 5
```

---

### `mcts`

| | |
|---|---|
| **Type** | `integer` |
| **Default** | `10` |

Maximum concurrent tasks setting stored in configuration. Manage it with:

```bash
chegi config set mcts 8
```

> **Note:** `chegi scan` uses the `--workers` flag (default `5`) for concurrency at runtime. The `mcts` value is persisted for future use across cheGi features.

---

### `sensitive_patterns`

| | |
|---|---|
| **Type** | `string[]` |
| **Used by** | `chegi guard`, `chegi scan --security`, `chegi guard history` |
| **Default** | `[]` |

Additional filename patterns for the Security Guard to flag as sensitive. Patterns use glob-style matching (e.g. `*.tfstate`, `kubeconfig*`) and are case-insensitive.

Custom patterns are merged with the built-in defaults at scan time. Files matching either built-in or custom patterns are flagged.

**CLI example:**

```bash
chegi config set sensitive_patterns '["*.tfstate", "*.backup"]'
```

**Manual JSON:**

```json
{
    "sensitive_patterns": [
        "*.tfstate",
        "kubeconfig*"
    ]
}
```

You can also manage patterns via `.chegi/guard-rules.json` (created by `chegi init`), which is loaded alongside `sensitive_patterns` from the config.

---

### `mirrors`

| | |
|---|---|
| **Type** | `object` |
| **Used by** | `chegi setup` |
| **Default** | `{}` |

Maps package managers to mirror or registry URLs. Used during `chegi setup` to speed up downloads in regions with slow default registries.

**Supported package managers:**

`pip` · `npm` · `yarn` · `gem` · `cargo` · `composer`

**Single URL:**

```json
{
    "mirrors": {
        "pip": ["https://pypi.example.com/simple"],
        "npm": ["https://registry.npmmirror.com"]
    }
}
```

**Multiple URLs per manager** (first URL is used as primary during setup):

```json
{
    "mirrors": {
        "pip": [
            "https://mirror-a.example.com/simple",
            "https://mirror-b.example.com/simple"
        ]
    }
}
```

A string value is also accepted and converted to a list internally:

```json
{
    "mirrors": {
        "npm": "https://registry.npmmirror.com"
    }
}
```

**CLI examples:**

```bash
chegi config mirror-add pip https://pypi.example.com/simple
chegi config mirror-remove npm
chegi config mirror-clear
```

During `chegi setup`, if mirrors are configured, cheGi offers to use them automatically or pick from saved options.

---

## Common Scenarios

### Large projects folder

Scan many repos without diving too deep:

```bash
chegi config set max_depth 4
chegi config exclude-add .next
chegi config exclude-add .turbo
chegi scan ~/projects
```

### Slow package downloads

Set mirrors once, use them in every setup:

```bash
chegi config mirror-add pip https://pypi.tuna.tsinghua.edu.cn/simple
chegi config mirror-add npm https://registry.npmmirror.com
chegi setup python -y
```

### Multiple workspaces

Each folder can have its own `.chegi.json`:

```bash
chegi config list --path ~/work
chegi config list --path ~/personal
```

---

## CLI vs Manual Editing

| Approach | When to use |
|----------|-------------|
| `chegi config` | Day-to-day changes, mirrors, excludes |
| Manual JSON edit | Bulk updates, copying config between machines |

After manual edits, verify with:

```bash
chegi config list
```

---

## Troubleshooting

### Config changes have no effect on scan depth

`chegi scan --max-depth` overrides the config file for that run only. Remove the flag to use `.chegi.json`.

### Mirrors not applied during setup

- Only supported package managers are loaded (`pip`, `npm`, `yarn`, `gem`, `cargo`, `composer`)
- Unsupported keys in `mirrors` are silently ignored on load
- Run `chegi config list` to confirm mirrors are saved

### Malformed JSON

If `.chegi.json` contains invalid JSON, cheGi falls back to defaults and ignores the file content. Fix the JSON or delete the file to regenerate via CLI.

### `exclude_dirs` still scans a folder

`exclude_dirs` matches directory **names** only, not paths. A folder named `vendor` is excluded everywhere; `my-project/vendor` is excluded by the name `vendor`, not by the full path.

---

## Global Configuration

cheGi also stores user-level preferences in `~/.config/chegi/config.json`. This file is managed automatically by the first-run wizard and is separate from per-project `.chegi.json` settings.

### `theme`

| | |
|---|---|
| **Type** | `string` |
| **Default** | `"default"` |

The active color theme for cheGi terminal output. Available themes:

| Key | Label |
|-----|-------|
| `default` | Default |
| `hacker` | Hacker |

Set via the first-run wizard's theme picker step. Example global config:

```json
{
    "theme": "hacker"
}
```

The setting persists across sessions and affects all `TerminalUI` output as well as table rendering.

## See Also

- [config command reference](commands/config.md) — all `chegi config` subcommands
- [scan command reference](commands/scan.md) — how scan uses config
- [setup command reference](commands/setup.md) — how setup uses mirrors
