"""Custom exceptions for Git operations."""


class GitCoreError(Exception):
    """Base exception for all Git-related errors."""

    pass


class GitCommandError(GitCoreError):
    """Raised when a git command fails."""

    pass


class GitNotInstalledError(GitCoreError):
    """Raised when git is not found on the system."""

    pass


class InvalidGitArgumentError(GitCoreError):
    """Raised when an invalid argument is passed to a git operation."""

    pass
