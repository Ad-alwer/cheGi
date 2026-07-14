"""Service for installing and removing Git hooks."""

import stat
from pathlib import Path

from chegi.services.git.client import GitClient
from chegi.services.hooks.constants import (
    CHEGI_HOOK_MARKER,
    HOOKS_DIR,
    PRE_COMMIT_FILENAME,
    PRE_COMMIT_TEMPLATE,
)
from chegi.services.hooks.exceptions import HookInstallError, HookRemoveError
from chegi.services.hooks.models import HookInfo


class HooksService:
    """Manages Git hooks with cheGi guard integration.

    Provides install and remove operations for a pre-commit hook
    that auto-runs ``chegi guard --fix`` before every commit.
    """

    def __init__(self, repo_path: Path):
        """Initializes the HooksService.

        Args:
            repo_path: Path to the Git repository root.
        """
        self.repo_path = repo_path

    def _git_dir(self) -> Path:
        """Returns the .git directory path for the repository.

        Returns:
            The .git directory path.

        Raises:
            HookInstallError: If the repository is not a valid Git repo.
        """
        git_client = GitClient(self.repo_path)
        if not git_client.is_valid_repo():
            raise HookInstallError(f"Not a valid Git repository: {self.repo_path}")
        return self.repo_path / ".git"

    def _hook_path(self) -> Path:
        """Returns the full path to the pre-commit hook.

        Returns:
            The pre-commit hook file path.
        """
        return self.repo_path / HOOKS_DIR / PRE_COMMIT_FILENAME

    def is_installed(self) -> HookInfo:
        """Checks whether the cheGi pre-commit hook is installed.

        Returns:
            A HookInfo dataclass with installation status and path.
        """
        hook_path = self._hook_path()
        if not hook_path.exists():
            return HookInfo(installed=False, path=str(hook_path))

        content = hook_path.read_text()
        is_chegi = CHEGI_HOOK_MARKER in content
        return HookInfo(
            installed=is_chegi,
            path=str(hook_path),
        )

    def install(self, force: bool = False) -> Path:
        """Installs a pre-commit hook that runs ``chegi guard --fix``.

        The hook script is written to ``.git/hooks/pre-commit`` and
        made executable. If a pre-commit hook already exists, the
        operation is skipped unless ``force=True``.

        Args:
            force: If True, overwrite any existing pre-commit hook.

        Returns:
            The path to the installed hook file.

        Raises:
            HookInstallError: If installation fails (not a Git repo,
                existing hook without force, or write error).
        """
        self._git_dir()

        hook_path = self._hook_path()
        hooks_dir = hook_path.parent
        hooks_dir.mkdir(parents=True, exist_ok=True)

        if hook_path.exists() and not force:
            content = hook_path.read_text()
            if CHEGI_HOOK_MARKER in content:
                raise HookInstallError(
                    "cheGi pre-commit hook is already installed. "
                    "Use --force to reinstall."
                )
            raise HookInstallError(
                "A pre-commit hook already exists. Use --force to overwrite."
            )

        try:
            hook_path.write_text(PRE_COMMIT_TEMPLATE)
            hook_path.chmod(
                hook_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
            )
        except OSError as exc:
            raise HookInstallError(f"Failed to write pre-commit hook: {exc}") from exc

        return hook_path

    def remove(self) -> bool:
        """Removes the cheGi pre-commit hook if installed.

        Only removes hooks that contain the cheGi marker comment.
        Non-cheGi hooks are left untouched.

        Returns:
            True if the hook was removed, False if no cheGi hook was found.

        Raises:
            HookRemoveError: If the hook exists but cannot be removed.
        """
        hook_path = self._hook_path()

        if not hook_path.exists():
            return False

        content = hook_path.read_text()
        if CHEGI_HOOK_MARKER not in content:
            return False

        try:
            hook_path.unlink()
        except OSError as exc:
            raise HookRemoveError(f"Failed to remove pre-commit hook: {exc}") from exc

        return True
