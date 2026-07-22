"""Public API re-exports for the Git client, status model, and exceptions."""

from .client import GitClient
from .constants import MIN_GIT_VERSION
from .exceptions import GitCommandError, GitCoreError, GitNotInstalledError
from .models import GitStatus

__all__ = [
    "GitClient",
    "GitStatus",
    "GitCoreError",
    "GitCommandError",
    "GitNotInstalledError",
    "MIN_GIT_VERSION",
]
