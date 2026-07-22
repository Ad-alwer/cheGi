# Contributing to cheGi

Thank you for your interest in contributing to **cheGi** — *The ultimate Git companion. Type less, do more.*

Have a good idea or want to add a feature? You're welcome to contribute. Every contribution should follow the standards in this guide — tests, linting, code structure, and the existing project conventions. That keeps cheGi reliable and consistent for everyone.

Questions or ideas before you start? Reach out at **alwer.dev@gmail.com**.

## Getting Started

### Prerequisites

- Python 3.8+
- Git

### Development Setup

```bash
git clone https://github.com/Ad-alwer/cheGi.git
cd cheGi
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Verify the CLI is available:

```bash
chegi --help
```

## Project Structure

```
src/chegi/
├── cli/           # Typer commands and preflight checks
├── services/      # Business logic (scanner, git, guard, sync, ...)
├── config/        # .chegi.json management
└── ui/            # Rich terminal output
tests/             # pytest test suite
```

## Running Tests

```bash
pytest -v
```

Run a specific test file:

```bash
pytest tests/cli/commands/test_scan.py -v
```

Every new feature or bug fix must include tests. Aim to keep coverage high — don't leave untested paths. All tests must pass before committing.

## Code Style

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
ruff check src tests
ruff format src tests
```

Guidelines:

- Match existing patterns in the module you are editing
- Keep CLI logic thin — put business logic in `services/`
- Add or update tests for behavior changes
- Use [Google-style docstrings](https://google.github.io/styleguide/pyguide.html#s3.8-comments-and-docstrings) for all functions (one-line for trivial getters/setters)
- Add a short one-line docstring at the top of every file describing its purpose
- Test functions must have one-line docstrings describing the scenario
- Keep commits small and focused with clear commit messages

### Type Hints (STRICT — Zero Tolerance)

Every function, method, and callable MUST have complete type hints. No exceptions.

```python
# WRONG
def process(data, count):
    return data[:count]

# RIGHT
def process(data: str, count: int) -> str:
    return data[:count]
```

Rules:
- Every `def` MUST have a return type annotation (`-> Type` or `-> None`)
- Every `__init__` MUST have `-> None`
- Every parameter MUST have a type hint
- Use `Optional[X]` for nullable params, `List[X]`, `Dict[K, V]` from `typing`
- `self`/`cls` do NOT need type hints
- Properties MUST have return type annotations

Before committing, verify with:
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

## Pull Requests

1. Fork the repository and create a feature branch from `main`
2. Make focused changes with clear commit messages
3. Ensure tests pass: `pytest -v`
4. Ensure lint passes: `ruff check src tests`
5. Open a pull request with a short description of **what** changed and **why**

## Reporting Issues

- Use [GitHub Issues](https://github.com/Ad-alwer/cheGi/issues) for bugs and feature requests
- Include your OS, Python version, cheGi version, and steps to reproduce
- For security issues, see [SECURITY.md](SECURITY.md)

## Documentation

Documentation lives in `docs/` and is built with [MkDocs Material](https://squidfunk.github.io/mkdocs-material/).

```bash
pip install -e ".[docs]"
mkdocs serve        # preview at http://127.0.0.1:8000
mkdocs build --strict
```

The site deploys automatically to GitHub Pages on push to `main` when files under `docs/` or `mkdocs.yml` change.

Live site: [ad-alwer.github.io/cheGi](https://ad-alwer.github.io/cheGi/)

## Releases

Releases are triggered by pushing a version tag (`v*`), which:

1. Builds cross-platform binaries via GitHub Actions
2. Publishes the package to PyPI

Update `version` in `pyproject.toml` and `__version__` in `src/chegi/__init__.py` before tagging.
