# `chegi co` / `br` / `ci` / `st`

Shortcut aliases for common Git commands. Every argument after the alias
is passed through directly to Git — no transformation, no surprises.

## Usage

| cheGi | equivalent |
|-------|-----------|
| `chegi co <branch>` | `git checkout <branch>` |
| `chegi co -b <name>` | `git checkout -b <name>` |
| `chegi br` | `git branch` |
| `chegi br -a` | `git branch -a` |
| `chegi ci -m "msg"` | `git commit -m "msg"` |
| `chegi st` | `git status` |
| `chegi st -s` | `git status -s` |

## What it does

These are thin wrappers — they construct `["git", "<subcommand>", ...args]`
and run it. No extra logic, no side effects.

## Related

- [chegi setup](setup.md) runs the wizard, which can auto-configure
  `git config --global alias.co checkout` etc.
- [chegi config](../configuration.md) for customising cheGi behaviour.
