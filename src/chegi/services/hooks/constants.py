"""Constants for the hooks service."""

from enum import Enum
from pathlib import Path


class HookType(str, Enum):
    """Type of Git hook managed by cheGi."""

    PRE_COMMIT = "pre-commit"
    PRE_PUSH = "pre-push"


HOOKS_DIR = Path(".git") / "hooks"

HOOK_FILENAMES = {
    HookType.PRE_COMMIT: "pre-commit",
    HookType.PRE_PUSH: "pre-push",
}

HOOK_MARKERS = {
    HookType.PRE_COMMIT: "# cheGi pre-commit hook",
    HookType.PRE_PUSH: "# cheGi pre-push hook",
}

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

PRE_PUSH_TEMPLATE = """\
#!/bin/sh
# cheGi pre-push hook — auto-guard before git push
# Installed by: chegi hooks install --pre-push
# Description: Runs `chegi guard` before each push.
#   Checks staged files and unpushed commits for sensitive data.
#   If sensitive files are detected, aborts the push.

CHEGI_GUARD_OUTPUT=$(chegi guard --fix 2>&1)
CHEGI_GUARD_EXIT=$?

if [ $CHEGI_GUARD_EXIT -ne 0 ]; then
    echo ""
    echo "  🔒 cheGi Security Guard detected sensitive files."
    echo "  Run 'chegi guard' manually for details."
    echo "  Push aborted."
    echo ""
    exit 1
fi

UNPUSHED=$(git rev-list --count @{u}..HEAD 2>/dev/null)
if [ "$UNPUSHED" != "" ] && [ "$UNPUSHED" -gt 0 ]; then
    CHEGI_SCAN_OUTPUT=$(chegi guard --scan . 2>&1)
    CHEGI_SCAN_EXIT=$?
    if [ $CHEGI_SCAN_EXIT -ne 0 ]; then
        echo ""
        echo "  🔒 cheGi found sensitive files in unpushed commits."
        echo "  Run 'chegi guard --history' for full details."
        echo "  Push aborted."
        echo ""
        exit 1
    fi
fi

exit 0
"""

HOOK_TEMPLATES = {
    HookType.PRE_COMMIT: PRE_COMMIT_TEMPLATE,
    HookType.PRE_PUSH: PRE_PUSH_TEMPLATE,
}
