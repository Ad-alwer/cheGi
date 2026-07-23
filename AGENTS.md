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

## Security & Execution Rules

- **NEVER execute commands without user permission** — always ask first
- **Git operations** (commit, push, pull, merge, rebase) — ALWAYS ask user before executing
- **Package installs** (pip, npm, apt) — ALWAYS ask user before executing
- **Destructive operations** (delete files, force push, drop branches) — ALWAYS ask and confirm
- **File modifications** — present diff for review before applying
- **System commands** (chmod, chown, rm -rf) — ALWAYS ask with clear warning
- **Exception**: Read-only commands (ls, cat, grep, git status, git log) are safe to run without asking

## Changelog (CRITICAL)

- **EVERY notable change** (feat/fix/refactor) MUST have a corresponding entry in `CHANGELOG.md`
- Format: Keep a Changelog (`## [version] - YYYY-MM-DD`, sections: `Added` / `Changed` / `Fixed` / `Removed`)
- Every version bump MUST get a new dated entry
- NEVER skip or forget changelog — this is enforced as a pre-commit gate
- **Before any commit**: verify CHANGELOG.md has been updated for the change being committed

## Testing

- Every change in `services/` needs new/updated tests
- Every CLI change needs `CliRunner` tests
- Tests must be added wherever new functionality or bug fixes are introduced
- Test coverage must remain high — don't leave untested paths
- **BEFORE COMMIT CHECKLIST (ALL MUST PASS):**
  - `pytest -v` (all pass)
  - `ruff check src tests` (no errors)
  - `ruff format src tests` (no issues)
  - `mkdocs build --strict` (no broken links)
  - **`CHANGELOG.md` updated for this change**
  - **All functions have type hints (return type + parameter types)**

## Architecture

- CLI layer (`cli/commands/`) must be thin — business logic in `services/`
- Each service module has its own `models.py` (dataclasses), `exceptions.py`, `constants.py`
- Never use `subprocess.run` directly in services — use `GitClient.run_command()`
- Never use `shell=True` — always use command lists and `shlex`
- Don't replace environment variables — merge with `os.environ.copy()`
- Never `except Exception: pass` — catch specific exceptions
- Every `tests/services/*/` directory MUST have an `__init__.py`
- Never raise `ValueError`, `TypeError`, or `RuntimeError` in services — write custom exceptions

## UX Philosophy

- **questionary-first**: All interactive CLI commands MUST use `questionary` for step-by-step guided flows
- User should never face a bare prompt — always provide context, suggestions, and previews
- Guided flow (no flags) walks the user through the process; flags provide fast-path for power users
- Every interactive step should have clear defaults, validation, and a way to go back
- Brand elements (🐆, mascot, colors) should be present but not overwhelming
- The goal: "Type less, do more" — make the user feel assisted, not questioned

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

- Double quotes (matching `pyproject.toml` config)
- Max line length: 88
- Variables/functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`

## Type Hints (STRICT — Zero Tolerance)

Every function, method, and callable MUST have complete type hints. No exceptions.

### Rules

- Every `def` MUST have a return type annotation: `-> Type` or `-> None`
- Every `__init__` MUST have `-> None`
- Every parameter MUST have a type hint — never write `def foo(bar):`
- Use `Optional[X]` for parameters that can be `None`, not just `X`
- Use `List[X]`, `Dict[K, V]`, `Tuple[X, ...]` from `typing` (not bare `list`, `dict`, `tuple` for Python 3.8 compat)
- `self` and `cls` do NOT need type hints
- Properties MUST have return type annotations
- Lambda expressions are exempt

### Examples

```python
# WRONG
def process(data, count):
    return data[:count]

def __init__(self, name):
    self.name = name

# RIGHT
def process(data: str, count: int) -> str:
    return data[:count]

def __init__(self, name: str) -> None:
    self.name = name
```

### Pre-commit Gate

Before ANY commit, run the AST type-check test to verify zero violations:
```bash
python -c "
import ast, os
issues = []
for root, dirs, files in os.walk('src/chegi'):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    for f in files:
        if not f.endswith('.py'): continue
        path = os.path.join(root, f)
        tree = ast.parse(open(path).read())
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.returns is None:
                    issues.append(f'{path}:{node.lineno} {node.name}() missing return type')
                for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
                    if arg.arg not in ('self', 'cls') and arg.annotation is None:
                        issues.append(f'{path}:{node.lineno} {node.name}() param \"{arg.arg}\" missing type')
if issues:
    for i in issues: print(i)
    raise SystemExit(f'FAILED: {len(issues)} type hint violations')
print('OK: all type hints present')
"
```

If this script reports ANY violations, fix them before committing.
