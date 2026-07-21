"""Service for installing and removing Git hooks."""

import stat
from pathlib import Path

from chegi.services.git.client import GitClient
from chegi.services.hooks.constants import (
    HOOK_FILENAMES,
    HOOK_MARKERS,
    HOOK_TEMPLATES,
    HOOKS_DIR,
    HookType,
)
from chegi.services.hooks.exceptions import HookInstallError, HookRemoveError
from chegi.services.hooks.models import HookInfo


class HooksService:
    """Manages Git hooks with cheGi guard integration.

    Provides install, remove, and status operations for Git hooks
    (pre-commit, pre-push) that auto-run cheGi guard.
    """

    def __init__(self, repo_path: Path) -> None:
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

    def _hook_path(self, hook_type: HookType = HookType.PRE_COMMIT) -> Path:
        """Returns the full path to the specified hook file.

        Args:
            hook_type: The type of hook to get the path for.

        Returns:
            The hook file path.
        """
        filename = HOOK_FILENAMES[hook_type]
        return self.repo_path / HOOKS_DIR / filename

    def _marker(self, hook_type: HookType) -> str:
        """Returns the cheGi marker comment for the given hook type.

        Args:
            hook_type: The type of hook.

        Returns:
            The marker string.
        """
        return HOOK_MARKERS[hook_type]

    def _template(self, hook_type: HookType) -> str:
        """Returns the hook script template for the given hook type.

        Args:
            hook_type: The type of hook.

        Returns:
            The template string.
        """
        return HOOK_TEMPLATES[hook_type]

    def _type_name(self, hook_type: HookType) -> str:
        """Returns a human-readable name for the hook type.

        Args:
            hook_type: The type of hook.

        Returns:
            Display name like \"pre-commit\" or \"pre-push\".
        """
        return hook_type.value

    def is_installed(self, hook_type: HookType = HookType.PRE_COMMIT) -> HookInfo:
        """Checks whether the cheGi hook of the given type is installed.

        Args:
            hook_type: The type of hook to check.

        Returns:
            A HookInfo dataclass with installation status and path.
        """
        hook_path = self._hook_path(hook_type)
        if not hook_path.exists():
            return HookInfo(installed=False, path=str(hook_path))

        content = hook_path.read_text()
        is_chegi = self._marker(hook_type) in content
        return HookInfo(
            installed=is_chegi,
            path=str(hook_path),
        )

    def install(
        self,
        hook_type: HookType = HookType.PRE_COMMIT,
        force: bool = False,
    ) -> Path:
        """Installs a Git hook that runs cheGi guard.

        The hook script is written to ``.git/hooks/<name>`` and
        made executable. If a hook already exists, the operation
        is skipped unless ``force=True``.

        Args:
            hook_type: The type of hook to install.
            force: If True, overwrite any existing hook.

        Returns:
            The path to the installed hook file.

        Raises:
            HookInstallError: If installation fails.
        """
        self._git_dir()

        hook_path = self._hook_path(hook_type)
        hooks_dir = hook_path.parent
        hooks_dir.mkdir(parents=True, exist_ok=True)

        type_name = self._type_name(hook_type)

        if hook_path.exists() and not force:
            content = hook_path.read_text()
            if self._marker(hook_type) in content:
                raise HookInstallError(
                    f"cheGi {type_name} hook is already installed. "
                    "Use --force to reinstall."
                )
            raise HookInstallError(
                f"A {type_name} hook already exists. Use --force to overwrite."
            )

        try:
            hook_path.write_text(self._template(hook_type))
            hook_path.chmod(
                hook_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
            )
        except OSError as exc:
            raise HookInstallError(f"Failed to write {type_name} hook: {exc}") from exc

        return hook_path

    def remove(self, hook_type: HookType = HookType.PRE_COMMIT) -> bool:
        """Removes the cheGi hook of the given type if installed.

        Only removes hooks that contain the cheGi marker comment.
        Non-cheGi hooks are left untouched.

        Args:
            hook_type: The type of hook to remove.

        Returns:
            True if the hook was removed, False if no cheGi hook was found.

        Raises:
            HookRemoveError: If the hook exists but cannot be removed.
        """
        hook_path = self._hook_path(hook_type)
        type_name = self._type_name(hook_type)

        if not hook_path.exists():
            return False

        content = hook_path.read_text()
        if self._marker(hook_type) not in content:
            return False

        try:
            hook_path.unlink()
        except OSError as exc:
            raise HookRemoveError(f"Failed to remove {type_name} hook: {exc}") from exc

        return True
