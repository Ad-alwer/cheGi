# chegi init

Initialize a cheGi project with a `.chegi/` directory.

## Synopsis

```bash
chegi init [PATH] [OPTIONS]
```

## Description

`chegi init` creates a `.chegi/` directory in your project root with default configuration files. This enables per-project settings for guard rules, ignore patterns, and cheGi configuration.

When you run `chegi init`, the following files are created:

| File | Purpose |
|------|---------|
| `.chegi/config.json` | Project-specific cheGi configuration (overrides global `.chegi.json`) |
| `.chegi/guard-rules.json` | Custom sensitive file patterns for `chegi guard` |
| `.chegi/.chegiignore` | Patterns to exclude from scans (`.gitignore` syntax) |

The command also adds `.chegi/` to `.gitignore` to prevent committing the directory.

## Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--force` | `-f` | Overwrite existing `.chegi/` directory | `false` |

## Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `PATH` | Project root directory | `.` (current directory) |

## Examples

Initialize the current directory as a cheGi project:

```bash
chegi init
```

Initialize a specific project:

```bash
chegi init ~/projects/my-app
```

Re-initialize (overwrite existing `.chegi/`):

```bash
chegi init --force
```

## Generated Files

### `.chegi/config.json`

Default project configuration:

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
  "guard_rules": [],
  "guard_excludes": []
}
```

### `.chegi/guard-rules.json`

Default sensitive patterns:

```json
{
  "patterns": [
    ".env*",
    "*.pem",
    "*.key",
    "id_rsa*",
    "id_ecdsa*",
    "id_ed25519*",
    "*.pk8",
    "*secret*",
    "credentials.json",
    "*.jwt",
    "*.token",
    ".npmrc",
    ".dockercfg",
    "docker.json",
    "service-account*.json",
    "aws-credentials.json",
    "*.credential",
    "*.cred",
    "*.passwd"
  ],
  "exclude_patterns": [
    "*.example.env",
    "*.sample.key",
    "*.test.env",
    "docs/*"
  ]
}
```

## See Also

- [guard](guard.md) — scan staged files for sensitive data
- [Configuration Guide](../configuration.md) — all configuration options
