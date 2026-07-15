# `chegi repo`

List and manage your GitHub repositories.

## Prerequisites

A GitHub token stored via `chegi auth login` is required.
Run `chegi auth login` first if you haven't already.

## Subcommands

### `repo list`

Display your GitHub repositories.

**Interactive mode (default):**

```bash
chegi repo list
```

Shows a fuzzy-searchable list of your repos. Type to filter, press Enter to select,
then choose an action (open in browser, copy URL, etc.).

**Table mode:**

```bash
chegi repo list --format table
```

**JSON mode:**

```bash
chegi repo list --format json
```

#### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--format` | `-f` | Output format: `interactive`, `table`, `json` |
| `--public` | | Show only public repositories |
| `--private` | | Show only private repositories |
| `--owner` | | Show only non-fork repositories |
| `--limit` | `-n` | Limit number of repositories |
| `--sort` | | Sort by: `stars` or `updated` |
| `--refresh` | | Force refresh from GitHub API (skip cache) |

#### Examples

```bash
# Interactive picker
chegi repo list

# Top 10 most starred
chegi repo list --sort stars --limit 10

# Only private repos as JSON
chegi repo list --private --format json

# Only owned public repos in table format
chegi repo list --owner --public --format table

# Fresh data, bypass cache
chegi repo list --refresh
```

#### Caching

Repositories are cached locally in `~/.config/chegi/repo_cache.json`
for 5 minutes to avoid hitting the GitHub API on every invocation.
Use `--refresh` to force a fresh fetch.

---

## See Also

- [chegi auth](auth.md) — manage GitHub tokens
- [chegi new](new.md) — create projects and push to GitHub
