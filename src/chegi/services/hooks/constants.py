"""Constants for the hooks service."""

from pathlib import Path

HOOKS_DIR = Path(".git") / "hooks"
PRE_COMMIT_FILENAME = "pre-commit"
PRE_COMMIT_PATH = HOOKS_DIR / PRE_COMMIT_FILENAME

CHEGI_HOOK_MARKER = "# cheGi pre-commit hook"

PRE_COMMIT_TEMPLATE = """\
#!/bin/sh
# cheGi pre-commit hook — auto-guard on every git commit
# Installed by: chegi hooks install
# Description: Runs `chegi guard --fix` before each commit.
#   If sensitive files are detected, unstages them and aborts the commit.

CHEGI_GUARD_OUTPUT=$(chegi guard --fix 2>&1)
CHEGI_GUARD_EXIT=$?

if [ $CHEGI_GUARD_EXIT -ne 0 ]; then
    echo ""
    echo "  🔒 cheGi Security Guard detected sensitive files."
    echo "  Run 'chegi guard' manually for details."
    echo "  Commit aborted."
    echo ""
    exit 1
fi

exit 0
"""
