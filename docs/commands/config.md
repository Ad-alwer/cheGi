# chegi config

Manage cheGi workspace settings stored in `.chegi.json`.

## Synopsis

```bash
chegi config <SUBCOMMAND> [ARGS] [OPTIONS]
```

## Description

Configuration is stored in `.chegi.json` at the base path you specify (default: current directory). Settings affect scanning behavior and package-manager mirrors used by `chegi setup`.

### Default Configuration File

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

### Configuration Keys

| Key | Type | Description | Default |
|-----|------|-------------|---------|
| `exclude_dirs` | `string[]` | Directory names skipped during `chegi scan` | see above |
| `max_depth` | `int` | Maximum directory traversal depth | `3` |
| `mcts` | `int` | Maximum concurrent tasks setting | `10` |
| `mirrors` | `object` | Package-manager mirror URLs | `{}` |
| `sensitive_patterns` | `string[]` | Extra filename patterns for Security Guard | `[]` |

### Supported Package Managers (mirrors)

`pip`, `npm`, `yarn`, `gem`, `cargo`, `composer`

---

## Subcommands

### `config list`

Show the current configuration.

```bash
chegi config list [--path PATH]
```

| Option | Short | Default |
|--------|-------|---------|
| `--path` | `-p` | `.` |

**Example:**

```bash
chegi config list
chegi config list --path ~/projects
```

---

### `config set`

Update an integer configuration key.

```bash
chegi config set KEY VALUE [--path PATH]
```

| Argument | Description |
|----------|-------------|
| `KEY` | `max_depth` or `mcts` (integer keys only) |
| `VALUE` | New integer value |

!!! note
    `sensitive_patterns` is a string array and cannot be set via `chegi config set`.
    Edit `.chegi.json` directly or use `.chegi/guard-rules.json` for custom patterns.

**Examples:**

```bash
chegi config set max_depth 5
chegi config set mcts 8
```

---

### `config exclude-add`

Add a directory name to the scan exclusion list.

```bash
chegi config exclude-add FOLDER [--path PATH]
```

**Example:**

```bash
chegi config exclude-add dist
chegi config exclude-add .mypy_cache
```

---

### `config exclude-remove`

Remove a directory name from the exclusion list.

```bash
chegi config exclude-remove FOLDER [--path PATH]
```

**Example:**

```bash
chegi config exclude-remove .vscode
```

Exits with code `1` if the folder is not in the exclusion list.

---

### `config mirror-add`

Add a mirror URL for a package manager.

```bash
chegi config mirror-add PM_NAME URL [--path PATH]
```

**Examples:**

```bash
chegi config mirror-add pip https://pypi.example.com/simple
chegi config mirror-add npm https://registry.npmmirror.com
```

---

### `config mirror-remove`

Remove mirror URL(s) for a package manager.

```bash
chegi config mirror-remove PM_NAME [URL] [--path PATH]
```

| Argument | Description |
|----------|-------------|
| `PM_NAME` | Package manager name |
| `URL` | Specific URL to remove; omit to remove all mirrors for that PM |

**Examples:**

```bash
chegi config mirror-remove pip https://pypi.example.com/simple
chegi config mirror-remove npm
```

---

### `config mirror-set-all`

Replace the entire mirrors configuration with a JSON object.

```bash
chegi config mirror-set-all JSON_DATA [--path PATH]
```

**Example:**

```bash
chegi config mirror-set-all '{"pip": "https://pypi.example.com/simple", "npm": ["https://registry.npmmirror.com"]}'
```

Values can be a single URL string or a list of URLs.

---

### `config mirror-clear`

Remove all configured mirrors.

```bash
chegi config mirror-clear [--path PATH]
```

**Example:**

```bash
chegi config mirror-clear
```

---

## Global Option

All subcommands accept:

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--path` | `-p` | Base directory where `.chegi.json` is stored | `.` |

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Invalid key, unknown folder, unsupported package manager, or bad JSON |

## See Also

- [scan](scan.md) — uses `max_depth` and `exclude_dirs`
- [setup](setup.md) — uses `mirrors` during installation
