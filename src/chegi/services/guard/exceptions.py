"""Custom exceptions for guard operations and history scanning failures."""


class GuardError(Exception):
    """Base exception for Guard operations."""

    pass


class HistoryScanError(GuardError):
    """Raised when a Git history scan fails."""

    pass
