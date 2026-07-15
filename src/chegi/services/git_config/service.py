"""Service for reading and writing Git global configuration."""

import os
import subprocess
from typing import Dict, List, Optional, Tuple

from chegi.services.git_config.exceptions import GitConfigError
from chegi.services.git_config.models import (
    GitConfigEntry,
)


def _run_git_config(args: List[str], check: bool = True) -> subprocess.CompletedProcess:
    """Runs a git config command and returns the result.

    Args:
        args: List of arguments after 'git config'.
        check: Whether to raise on non-zero exit.

    Returns:
        The CompletedProcess result.

    Raises:
        GitConfigError: If git is not found or the command fails.
    """
    try:
        return subprocess.run(
            ["git", "config"] + args,
            capture_output=True,
            text=True,
            check=check,
        )
    except FileNotFoundError:
        raise GitConfigError("Git is not installed.")
    except subprocess.CalledProcessError as e:
        raise GitConfigError(f"Git config failed: {e.stderr.strip() or e}")


_KNOWN_KEYS: List[Tuple[str, str, str]] = [
    ("user.name", "Your name", os.environ.get("USER", "")),
    ("user.email", "Your email", ""),
    ("init.defaultBranch", "Default branch name", "main"),
    ("core.editor", "Editor command", "code --wait"),
    ("pull.rebase", "Enable pull.rebase?", "true"),
    ("fetch.prune", "Enable fetch.prune?", "true"),
]

KNOWN_SETUP_KEYS = [(k, label, default) for k, label, default in _KNOWN_KEYS]


class GitConfigService:
    """Service for reading and writing Git global configuration."""

    @staticmethod
    def get_all() -> List[GitConfigEntry]:
        """Returns all global git config entries.

        Returns:
            List of GitConfigEntry objects.

        Raises:
            GitConfigError: If git is not available.
        """
        result = _run_git_config(["--global", "--list"])
        entries: List[GitConfigEntry] = []
        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if not line or "=" not in line:
                continue
            key, value = line.split("=", 1)
            entries.append(GitConfigEntry(key=key.strip(), value=value.strip()))
        return entries

    @staticmethod
    def get(key: str) -> Optional[str]:
        """Returns the value of a single git config key.

        Args:
            key: The config key (e.g. user.name).

        Returns:
            The value if set, None otherwise.
        """
        try:
            result = _run_git_config(["--global", key], check=True)
            val = result.stdout.strip()
            return val if val else None
        except GitConfigError:
            return None

    @staticmethod
    def set(key: str, value: str) -> None:
        """Sets a git global config value.

        Args:
            key: The config key.
            value: The value to set.

        Raises:
            GitConfigError: If the operation fails.
        """
        _run_git_config(["--global", key, value], check=True)

    @staticmethod
    def unset(key: str) -> None:
        """Unsets a git global config key.

        Args:
            key: The config key to remove.

        Raises:
            GitConfigError: If the operation fails.
        """
        try:
            _run_git_config(["--global", "--unset-all", key], check=True)
        except GitConfigError:
            pass

    @staticmethod
    def set_identity(name: str, email: str) -> None:
        """Sets user.name and user.email globally.

        Args:
            name: The user name.
            email: The user email.

        Raises:
            GitConfigError: If either operation fails.
        """
        GitConfigService.set("user.name", name)
        GitConfigService.set("user.email", email)

    @staticmethod
    def get_identity() -> Tuple[Optional[str], Optional[str]]:
        """Returns the current global user name and email.

        Returns:
            Tuple of (name, email), each may be None.
        """
        return (
            GitConfigService.get("user.name"),
            GitConfigService.get("user.email"),
        )

    @staticmethod
    def to_dict(entries: List[GitConfigEntry]) -> Dict[str, str]:
        """Converts a list of entries to a flat dict.

        Args:
            entries: List of GitConfigEntry.

        Returns:
            Dict mapping key -> value.
        """
        return {e.key: e.value for e in entries}
