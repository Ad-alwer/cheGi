"""Exceptions for the info service."""


class InfoError(Exception):
    """Base exception for info-related errors."""

    pass


class NotAGitRepoError(InfoError):
    """Raised when the target path is not inside a Git repository."""

    pass
