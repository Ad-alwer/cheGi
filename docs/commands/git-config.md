# `chegi config git`

View and modify Git global configuration — `user.name`, `user.email`,
`init.defaultBranch`, `core.editor`, and more.

## Synopsis

```bash
chegi config git set [KEY] [VALUE]
chegi config git get [KEY...]
```

## Subcommands

### `config git set`

Set Git global configuration values.

**Interactive wizard** (no arguments):

```bash
chegi config git set
```

Walks through 6 steps:

1. **User Name** — `user.name`
2. **User Email** — `user.email`
3. **Default Branch** — `init.defaultBranch`
4. **Core Editor** — `core.editor`
5. **Pull Rebase** — `pull.rebase` (yes/no)
6. **Fetch Prune** — `fetch.prune` (yes/no)

Each step shows the current value and writes immediately on change.
After the last step, a **Review & Revert** screen shows all changes
in a diff table. You can:

- Enter comma-separated keys to revert specific changes
- Leave empty to keep everything
- Choose **Start Over** to undo all changes and restart the wizard

**Direct mode:**

```bash
chegi config git set user.name "Ali Dehghani"
chegi config git set init.defaultBranch main
```

When `VALUE` is omitted, you are prompted interactively
with the current value as default.

---

### `config git get`

Display Git global configuration values.

**Interactive mode** (no arguments):

```bash
chegi config git get
```

Shows all Git config entries grouped by category
(User, Core, Alias, Init, Pull, Fetch, etc.).
Enter comma-separated keys to display specific values,
or leave empty to show everything.

**Direct mode:**

```bash
chegi config git get user.name
chegi config git get user.name user.email init.defaultBranch
```

---

## Categories

Keys are automatically categorised for display:

| Category | Example Keys | Icon |
|----------|-------------|------|
| User | `user.name`, `user.email` | 👤 |
| Core | `core.editor`, `core.pager` | ⚙️ |
| Init | `init.defaultBranch` | 🌱 |
| Pull | `pull.rebase`, `pull.ff` | ⬇️ |
| Fetch | `fetch.prune` | 📥 |
| Push | `push.default`, `push.autoSetupRemote` | 📤 |
| Alias | `alias.co`, `alias.br` | 🔗 |
| Protocol | `protocol.version` | 🌐 |
| Other | everything else | 📋 |

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | No value provided or no matching keys found |

## See Also

- [chegi config](config.md) — manage cheGi workspace settings
- [chegi init](init.md) — set Git identity during project initialisation
- [chegi setup](setup.md) — first-run wizard with identity setup
