"""Custom exceptions for the commit service."""


class CommitError(Exception):
    """Base exception for all commit-related errors."""


class CommitAbortedError(CommitError):
    """Raised when the user aborts the commit process."""


class NoStagedFilesError(CommitError):
    """Raised when there are no files staged for commit."""
