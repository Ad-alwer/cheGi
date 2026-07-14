"""Constants for the doctor service."""

from pathlib import Path

KEY_GITIGNORE_PATTERNS: list = [
    ".env",
    ".env.*",
    "*.key",
    "*.pem",
    "node_modules/",
    ".venv/",
    "__pycache__/",
    ".DS_Store",
    ".vscode/",
    ".idea/",
]

HOOKS_DIR = Path(".git") / "hooks"
PRE_COMMIT_HOOK_PATH = HOOKS_DIR / "pre-commit"
PRE_PUSH_HOOK_PATH = HOOKS_DIR / "pre-push"

GITIGNORE_FILENAME = ".gitignore"
CHEGI_DIR_NAME = ".chegi"
