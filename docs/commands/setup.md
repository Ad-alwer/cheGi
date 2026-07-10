# chegi setup

Install and configure a development environment.

## Synopsis

```bash
chegi setup ENVIRONMENT [OPTIONS]
```

## Description

`chegi setup` bootstraps a development toolchain for a given language or toolset. It reads environment presets bundled with cheGi, detects your OS package manager, checks which tools are already installed, and guides you through installing the rest.

Configured package-manager mirrors from `.chegi.json` are applied during installation when relevant.

## Arguments

| Argument | Description |
|----------|-------------|
| `ENVIRONMENT` | Language or toolset to set up (required) |

### Supported Environments

| Name | Description |
|------|-------------|
| `python` | Python development toolchain |
| `javascript` | Node.js / JavaScript tooling |
| `go` | Go development toolchain |
| `rust` | Rust development toolchain |
| `cpp` | C++ development toolchain |
| `csharp` | C# / .NET development toolchain |
| `ruby` | Ruby development toolchain |
| `apps` | General standalone applications (e.g. Postman) |

## Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--yes` | `-y` | Automatically accept all installation prompts | `false` |

## Examples

Set up a Python environment interactively:

```bash
chegi setup python
```

Set up Go with no prompts:

```bash
chegi setup go -y
```

Install a standalone app:

```bash
chegi setup postman
```

## Workflow

1. Resolve the target environment from presets
2. Detect the OS package manager (`apt`, `brew`, `choco`, etc.)
3. Check which tools are already installed
4. Let you select tools to install (unless `--yes`)
5. Apply configured mirrors from `.chegi.json`
6. Run installation commands

If all critical tools are already installed, cheGi exits with a success message.

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Setup completed or all tools already installed |
| `1` | Unknown environment, user aborted, or installation error |

## See Also

- [config](config.md) — configure package-manager mirrors used during setup
- [gitignore](gitignore.md) — generate a `.gitignore` after setting up a project
