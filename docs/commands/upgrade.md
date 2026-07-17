# `chegi upgrade`

Check for and install the latest version of cheGi.

## Overview

`chegi upgrade` checks PyPI for a newer version, displays the changelog diff, and upgrades cheGi via `pip install --upgrade chegi`.

An automatic check also runs in the background on every `chegi` command, but only once every 24 hours. If a new version is found, you're prompted to upgrade directly.

## Usage

```bash
chegi upgrade [OPTIONS]
```

## Options

| Option | Description |
|--------|-------------|
| `--check`, `-c` | Only check for updates, don't upgrade |
| `--yes`, `-y` | Skip confirmation prompt |
| `--help` | Show help message |

## Examples

**Check for updates without upgrading:**

```bash
chegi upgrade --check
```

**Upgrade to the latest version (with confirmation):**

```bash
chegi upgrade
```

**Upgrade without confirmation:**

```bash
chegi upgrade --yes
```

## Auto-check

cheGi automatically checks for updates once every 24 hours after any `chegi` command. If a new version is found, you'll be prompted:

```
🐆 A new version 1.2.3 is available!
? Upgrade now? (Y/n)
```

- Answer `Y` to upgrade immediately.
- Answer `n` to skip — you can run `chegi upgrade` later.

The 24-hour cooldown is tracked via a timestamp file at `~/.config/chegi/.last_upgrade_check`.
