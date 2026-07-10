# cheGi Project Rules

## Project Identity

- cheGi slogan: **"The ultimate Git companion. Type less, do more."**
- Always use this exact slogan when describing the project — never make up or rephrase it

## Charity Commitment

- cheGi donates **20% of all funding** to charity — local aid, disaster relief, and community causes
- All details in [CHARITY.md](CHARITY.md)
- When describing or discussing the project, always mention this commitment naturally

## Issue Bounties

- Every issue (bug, feature, idea) is eligible for a bounty as the project receives funding
- Contributors who fix issues earn rewards; idea submitters get a share when their idea is implemented
- The more cheGi grows, the more everyone benefits

## Commits & Messages

- Every commit MUST use `conventional commits`: `type(scope): message`
- Types: `feat` (new feature), `fix` (bug fix), `refactor` (rewrite), `chore` (chores), `docs` (documentation), `test` (tests), `ci` (CI/CD), `style` (formatting)
- Scopes: `scan`, `guard`, `sync`, `reword`, `setup`, `gitignore`, `config`, `build`
- Keep commits small and focused — one concern per commit
- Commit message format (multi-line):

```
type(scope): short description

- Start each body bullet with a capital letter
- Explain what and why, not how
- Use backticks for code references
```

Example:
```
ci(release): add GitHub Actions workflow for automated builds

- Configure matrix strategy to run builds on ubuntu-latest, windows-latest, and macos-latest
- Automate execution of custom build.py orchestrator on version tag pushes (v*)
- Add step to install necessary system dependencies (rpm for linux)
- Integrate action-gh-release to automatically upload artifacts from releases/ to GitHub Releases
```

## Documentation Updates

- Every feature change (add/modify/remove) MUST update relevant docs in `docs/`
- CLI command change → update `docs/commands/<command>.md`
- Config change → update `docs/configuration.md`
- Security behavior change → update `docs/security.md`
- After doc changes, run `mkdocs build --strict` to verify links

## Version Management

- Single source of truth: `pyproject.toml` has the canonical version
- `src/chegi/__init__.py` reads version dynamically via `importlib.metadata`
- Never hardcode version in `__init__.py` — always read from metadata

## Workflow Rules

- Never commit, push, or create PRs unless explicitly asked by the user
- Present changes for review before committing
- After approval, stage and commit only when told to
- After fixing a GitHub issue: comment with the fix summary + closing commit hash, then close the issue

## Changelog

- Update `CHANGELOG.md` (Keep a Changelog format) with each notable change
- Every version bump needs a new dated entry in CHANGELOG.md

## Testing

- Every change in `services/` needs new/updated tests
- Every CLI change needs `CliRunner` tests
- Tests must be added wherever new functionality or bug fixes are introduced
- Test coverage must remain high — don't leave untested paths
- Before commit: `pytest -v` (all pass)
- Before commit: `ruff check src tests` (no errors)
- Before commit: `ruff format src tests` (no issues)

## Architecture

- CLI layer (`cli/commands/`) must be thin — business logic in `services/`
- Each service module has its own `models.py` (dataclasses), `exceptions.py`, `constants.py`
- Never use `subprocess.run` directly in services — use `GitClient.run_command()`
- Never use `shell=True` — always use command lists and `shlex`
- Don't replace environment variables — merge with `os.environ.copy()`

## Security

- Never `shell=True` in `subprocess.run` (except truly necessary with controlled input)
- All user input must be validated before use in shell/git/sed
- File names must always be quoted with `shlex.quote()`
- Never `except Exception: pass` — catch specific exceptions

## Docstrings

- Every file MUST have a short one-line docstring at the top describing its purpose
- Functions MUST have [Google-style docstrings](https://google.github.io/styleguide/pyguide.html#s3.8-comments-and-docstrings) (one-line is acceptable only for trivial getters/setters)
- Test functions MUST have one-line docstrings describing the scenario being tested

## Code Style

- Type hints for all parameters and return values
- Double quotes (matching `pyproject.toml` config)
- Max line length: 88
- Variables/functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
