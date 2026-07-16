"""Exceptions for the clone service."""


class CloneError(Exception):
    """Base exception for clone-related errors."""

    pass


class CloneUrlError(CloneError):
    """Raised when the repository URL is invalid."""

    pass


class CloneAuthError(CloneError):
    """Raised when authentication is required but not available."""

    pass


class CloneTargetExistsError(CloneError):
    """Raised when the target directory already exists and is not empty."""

    pass
