"""Exceptions specific to the Reword service."""

from chegi.services.git.exceptions import GitCoreError


class RewordError(GitCoreError):
    """Base exception for errors that occur during the reword process."""

    pass


class InvalidRangeError(RewordError):
    """Raised when the commit range is invalid (start >= end)."""

    pass


class InvalidHashFormatError(RewordError):
    """Raised when the commit hash format is invalid."""

    pass
